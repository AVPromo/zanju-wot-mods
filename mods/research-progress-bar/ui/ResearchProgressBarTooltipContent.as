package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.Sprite;
    import flash.text.TextField;
    import flash.text.TextFormat;
    import flash.text.TextFormatAlign;

    public final class ResearchProgressBarTooltipContent {
        public static const SECTION_GAP:Number = 10;

        private static const TOOLTIP_FONT_NAME:String = ResearchProgressBarFonts.FONT_NAME;
        private static const TOOLTIP_TEXT_COLOR:uint = 0xE6DDC8;
        private static const TOOLTIP_MUTED_TEXT_COLOR:uint = 0xB8AC97;
        private static const TOOLTIP_HIGHLIGHT_TEXT_COLOR:uint = 0xF0CF74;
        private static const TOOLTIP_CLICK_HINT_TEXT_COLOR:uint = 0x5FB2F2;
        private static const TOOLTIP_ICON_SIZE:Number = 20;
        private static const TOOLTIP_COMPACT_ICON_SIZE:Number = TOOLTIP_ICON_SIZE;
        private static const TOOLTIP_ICON_LAYOUT_WIDTH:Number = TOOLTIP_ICON_SIZE;
        private static const TOOLTIP_ICON_GAP:Number = 6;
        private static const TOOLTIP_ROW_GAP:Number = 3;
        private static const TOOLTIP_COMPACT_ROW_GAP:Number = 1;
        private static const TOOLTIP_TITLE_SIZE:int = 16;
        private static const TOOLTIP_SUBTITLE_SIZE:int = 14;
        private static const TOOLTIP_BODY_SIZE:int = 14;
        private static const TOOLTIP_PROGRESS_GAP:Number = 8;
        private static const TOOLTIP_TEXT_FIELD_PADDING:Number = 8;

        // `keyIndex` is this section's 1-based number within an ambiguous overlapping
        // stack (0 when the stack is unambiguous). When set, the click hint reads
        // "Press N to research." instead of "Click to research.".
        public static function buildTooltipSection(entry:Object, keyIndex:int = 0):Sprite {
            var section:Sprite = new Sprite();
            var marker:Object = entry.marker;
            var markerCostXp:Number = Number(entry.costXp);
            var combatXp:Number = Number(entry.combatXp);
            var freeXp:Number = Number(entry.freeXp);
            var row:Sprite;
            var rowBounds:Object;
            var cursorY:Number = 0;
            var markerState:String = marker != null && marker.markerState !== undefined ? String(marker.markerState) : "";
            var prereq:Object;
            var prereqs:Array;
            var progressLabel:String = marker != null && marker.progressLabel !== undefined ? String(marker.progressLabel) : "Vehicle XP";
            var totalProgressLabel:String = marker != null && marker.totalProgressLabel !== undefined ? String(marker.totalProgressLabel) : "Total XP";
            var progressReadyText:String = marker != null && marker.progressReadyText !== undefined ? String(marker.progressReadyText) : "ready for research";
            var progressXpLeftFormat:String = marker != null && marker.progressXpLeftFormat !== undefined ? String(marker.progressXpLeftFormat) : "{xp} XP left";
            var singleProgressRow:Boolean = marker != null && marker.singleProgressRow !== undefined && Boolean(marker.singleProgressRow);
            var costWithPrereqsXp:Number = marker != null && marker.costWithPrereqsXp !== undefined && marker.costWithPrereqsXp != null ? Number(marker.costWithPrereqsXp) : NaN;
            var costWithPrereqsLabel:String = marker != null && marker.costWithPrereqsLabel !== undefined ? String(marker.costWithPrereqsLabel) : "Cost with prerequisites";
            var prerequisitesLabel:String = marker != null && marker.prerequisitesLabel !== undefined ? String(marker.prerequisitesLabel) : "Prerequisites";
            var isNotAvailable:Boolean = marker != null && marker.isAvailable !== undefined && !Boolean(marker.isAvailable);
            var hasCostWithPrereqs:Boolean = !isNaN(costWithPrereqsXp) && costWithPrereqsXp > 0;
            // Measure progress against the combined cost whenever the marker is
            // locked and a cost-with-prerequisites total is supplied: both concrete
            // prerequisite items (research mode) and the Tier 11 final node, whose
            // single prerequisite is the abstract "all other nodes" (no item list).
            var progressTargetXp:Number = isNotAvailable && hasCostWithPrereqs ? costWithPrereqsXp : markerCostXp;
            var preProgressRow:Sprite = createTooltipBodyRow(marker, "preProgressTooltipHtml", "preProgressTooltipText");
            var detailRow:Sprite = createDetailTooltipRow(marker);

            row = createTooltipTitleCostRow(marker, markerCostXp, combatXp, freeXp);
            row.y = cursorY;
            section.addChild(row);
            rowBounds = row.getBounds(row);
            cursorY += rowBounds.height + TOOLTIP_ROW_GAP;

            row = createTooltipSubtitleRow(marker);
            if (row != null) {
                row.y = cursorY;
                section.addChild(row);
                rowBounds = row.getBounds(row);
                cursorY += rowBounds.height + TOOLTIP_ROW_GAP;
            }

            row = createBlueprintTooltipRow(marker);
            if (row != null) {
                row.y = cursorY;
                section.addChild(row);
                rowBounds = row.getBounds(row);
                cursorY += rowBounds.height + TOOLTIP_ROW_GAP;
            }

            if (markerState == "completed") {
                if (marker != null && marker.completedTooltipHtml !== undefined && marker.completedTooltipHtml != null && String(marker.completedTooltipHtml).length > 0) {
                    row = createTooltipHtmlTextRow(
                        String(marker.completedTooltipHtml),
                        TOOLTIP_BODY_SIZE,
                        TOOLTIP_TEXT_COLOR,
                        false
                    );
                }
                else {
                    row = createTooltipTextRow(
                        resolveCompletedMarkerText(marker),
                        TOOLTIP_BODY_SIZE,
                        TOOLTIP_HIGHLIGHT_TEXT_COLOR,
                        true
                    );
                }
                row.y = cursorY;
                section.addChild(row);
                rowBounds = row.getBounds(row);
                cursorY += rowBounds.height + TOOLTIP_ROW_GAP;

                cursorY = appendClickHintRows(section, marker, combatXp, freeXp, cursorY, keyIndex);
                return section;
            }

            // The description sits directly below the title/blueprint -- above the
            // prerequisites section for a locked marker (e.g. the Tier 11 final
            // node), and above the progress table for an available one. Keep the
            // larger gap only when the progress table follows immediately;
            // otherwise tighten it so the description reads as part of the head.
            if (preProgressRow != null) {
                preProgressRow.y = cursorY;
                section.addChild(preProgressRow);
                rowBounds = preProgressRow.getBounds(preProgressRow);
                cursorY += rowBounds.height + (isNotAvailable ? TOOLTIP_ROW_GAP : TOOLTIP_PROGRESS_GAP);
            }

            if (marker != null && marker.isAvailable !== undefined && !Boolean(marker.isAvailable)) {
                // A marker blocked without a concrete prerequisite list (the Tier 11
                // minor/major bucket, locked behind other upgrades in the branching
                // tree) shows just a short muted line -- no "Prerequisites" heading,
                // item list, cost or progress table.
                if (marker.blockedText !== undefined && marker.blockedText != null && String(marker.blockedText).length > 0) {
                    row = createTooltipTextRow(
                        String(marker.blockedText),
                        TOOLTIP_BODY_SIZE,
                        TOOLTIP_MUTED_TEXT_COLOR,
                        false
                    );
                    row.y = cursorY;
                    section.addChild(row);
                    return section;
                }

                row = createTooltipTextRow(
                    prerequisitesLabel + ":",
                    TOOLTIP_BODY_SIZE,
                    TOOLTIP_MUTED_TEXT_COLOR,
                    false
                );
                row.y = cursorY;
                section.addChild(row);
                rowBounds = row.getBounds(row);
                cursorY += rowBounds.height + TOOLTIP_ROW_GAP;

                prereqs = marker != null && marker.missingPrereqs is Array ? marker.missingPrereqs as Array : [];
                for each (prereq in prereqs) {
                    row = createTooltipIconTextRow(
                        prereq != null && prereq.item_type !== undefined ? String(prereq.item_type) : "unknown",
                        resolveTooltipItemLabel(prereq),
                        TOOLTIP_BODY_SIZE,
                        TOOLTIP_TEXT_COLOR,
                        false,
                        TOOLTIP_COMPACT_ICON_SIZE,
                        int(ResearchProgressBarIconTint.colorForPrereq(prereq, combatXp, freeXp))
                    );
                    row.y = cursorY;
                    section.addChild(row);
                    rowBounds = row.getBounds(row);
                    cursorY += rowBounds.height + TOOLTIP_COMPACT_ROW_GAP;
                }

                if (prereqs.length == 0) {
                    row = createTooltipTextRow(
                        resolveLockedBehindText(marker),
                        TOOLTIP_BODY_SIZE,
                        TOOLTIP_TEXT_COLOR,
                        false
                    );
                    row.y = cursorY;
                    section.addChild(row);
                    // With no concrete prerequisite items to list (e.g. the Tier 11
                    // final node, locked behind the abstract "all other nodes")
                    // there is normally nothing more to show. When a combined cost
                    // is supplied, fall through instead so the cost-with-
                    // prerequisites row and the progress table still render.
                    if (!hasCostWithPrereqs) {
                        return section;
                    }
                    rowBounds = row.getBounds(row);
                    cursorY += rowBounds.height + TOOLTIP_ROW_GAP;
                }

                if (!isNaN(costWithPrereqsXp) && costWithPrereqsXp > 0) {
                    cursorY += TOOLTIP_ROW_GAP;
                    row = createTooltipHtmlTextRow(
                        buildTooltipHighlightedHtml(costWithPrereqsLabel + ": ", formatExactXpValue(costWithPrereqsXp), " XP", true),
                        TOOLTIP_BODY_SIZE,
                        TOOLTIP_MUTED_TEXT_COLOR,
                        false
                    );
                    row.y = cursorY;
                    section.addChild(row);
                    rowBounds = row.getBounds(row);
                    cursorY += rowBounds.height + TOOLTIP_ROW_GAP;
                }
            }

            var progressRows:Array = [buildTooltipProgressRowData(progressLabel, combatXp, progressTargetXp, progressReadyText, progressXpLeftFormat)];

            if (!singleProgressRow) {
                progressRows.push(buildTooltipProgressRowData(totalProgressLabel, combatXp + freeXp, progressTargetXp, progressReadyText, progressXpLeftFormat));
            }

            for each (row in createTooltipProgressRows(progressRows)) {
                row.y = cursorY;
                section.addChild(row);
                rowBounds = row.getBounds(row);
                cursorY += rowBounds.height + TOOLTIP_ROW_GAP;
            }

            if (detailRow != null) {
                cursorY += TOOLTIP_PROGRESS_GAP - TOOLTIP_ROW_GAP;
                detailRow.y = cursorY;
                section.addChild(detailRow);
                rowBounds = detailRow.getBounds(detailRow);
                cursorY += rowBounds.height + TOOLTIP_ROW_GAP;
            }

            cursorY = appendClickHintRows(section, marker, combatXp, freeXp, cursorY, keyIndex);

            return section;
        }

        // Appends the marker's blue click-hint line(s) to `section` starting at
        // `cursorY`, returning the advanced cursorY. A pick marker carries
        // `clickHintLines` (one row per line: left-click / right-click); the
        // research/toggle markers carry a single `clickHintText`. When `keyIndex`
        // is set (this section is a numbered entry in an ambiguous overlapping
        // stack), the numbered `keyHintText` template replaces the plain hint.
        private static function appendClickHintRows(section:Sprite, marker:Object, combatXp:Number, freeXp:Number, cursorY:Number, keyIndex:int = 0):Number {
            var hintLines:Array = resolveClickHintLines(marker, keyIndex);
            var row:Sprite;
            var rowBounds:Object;
            var idx:int;

            if (hintLines.length == 0) {
                return cursorY;
            }
            if (!ResearchProgressBarInteractions.isMarkerClickable(marker, combatXp, freeXp)) {
                return cursorY;
            }

            cursorY += TOOLTIP_PROGRESS_GAP - TOOLTIP_ROW_GAP;
            for (idx = 0; idx < hintLines.length; idx++) {
                row = createTooltipTextRow(String(hintLines[idx]), TOOLTIP_BODY_SIZE, TOOLTIP_CLICK_HINT_TEXT_COLOR, false);
                row.y = cursorY;
                section.addChild(row);
                rowBounds = row.getBounds(row);
                cursorY += rowBounds.height + TOOLTIP_ROW_GAP;
            }
            return cursorY;
        }

        private static function resolveClickHintLines(marker:Object, keyIndex:int = 0):Array {
            var lines:Array = [];
            var raw:Array;
            var idx:int;
            var text:String;

            if (marker == null) {
                return lines;
            }
            // In a numbered overlapping stack, "Press N to research." (from the
            // keyHintText template) stands in for the ambiguous single-click hint.
            if (keyIndex > 0 && marker.keyHintText !== undefined && marker.keyHintText != null) {
                text = String(marker.keyHintText).split("{key}").join(String(keyIndex));
                if (text.length > 0) {
                    lines.push(text);
                }
                return lines;
            }
            if (marker.clickHintLines is Array) {
                raw = marker.clickHintLines as Array;
                for (idx = 0; idx < raw.length; idx++) {
                    if (raw[idx] == null) {
                        continue;
                    }
                    text = String(raw[idx]);
                    if (text.length > 0) {
                        lines.push(text);
                    }
                }
                return lines;
            }
            if (marker.clickHintText !== undefined && marker.clickHintText != null) {
                text = String(marker.clickHintText);
                if (text.length > 0) {
                    lines.push(text);
                }
            }
            return lines;
        }

        public static function buildEliteStatusCounterHtml(text:String):String {
            var slashIndex:int;
            var leftPart:String;
            var rightPart:String;
            var suffix:String;
            var rightEnd:int;

            if (text == null) {
                return "";
            }

            slashIndex = text.indexOf("/");
            if (slashIndex > 0) {
                leftPart = rtrim(text.substr(0, slashIndex));
                rightPart = ltrim(text.substr(slashIndex + 1));
                rightEnd = rightPart.indexOf(" ");
                if (rightEnd >= 0) {
                    suffix = rightPart.substr(rightEnd);
                    rightPart = rightPart.substr(0, rightEnd);
                }
                else {
                    suffix = "";
                }

                return buildTooltipHighlightedHtml("", leftPart, "", true)
                    + escapeHtml("/")
                    + buildTooltipHighlightedHtml("", rightPart, suffix, true);
            }

            return escapeHtml(text);
        }

        private static function resolveLockedBehindText(marker:Object):String {
            var prereqNames:Array;
            var prereqText:String;

            if (marker != null && marker.missingPrereqNames is Array) {
                prereqNames = marker.missingPrereqNames as Array;
                if (prereqNames.length == 1) {
                    return String(prereqNames[0]);
                }
                if (prereqNames.length > 1) {
                    prereqText = prereqNames.join(", ");
                    return prereqText;
                }
            }

            return "missing prerequisites";
        }

        private static function resolveCompletedMarkerText(marker:Object):String {
            if (marker != null && marker.completedTooltipText !== undefined && marker.completedTooltipText != null) {
                if (String(marker.completedTooltipText).length > 0) {
                    return String(marker.completedTooltipText);
                }
            }

            if (marker != null && marker.completedLabel !== undefined && marker.completedLabel != null && String(marker.completedLabel).length > 0) {
                return String(marker.completedLabel);
            }

            return "Unlocked";
        }

        private static function createDetailTooltipRow(marker:Object):Sprite {
            return createTooltipBodyRow(marker, "detailTooltipHtml", "detailTooltipText");
        }

        private static function createTooltipBodyRow(marker:Object, htmlKey:String, textKey:String):Sprite {
            if (marker != null && marker[htmlKey] !== undefined && marker[htmlKey] != null) {
                if (String(marker[htmlKey]).length > 0) {
                    return createTooltipHtmlTextRow(
                        String(marker[htmlKey]),
                        TOOLTIP_BODY_SIZE,
                        TOOLTIP_TEXT_COLOR,
                        false
                    );
                }
            }

            if (marker != null && marker[textKey] !== undefined && marker[textKey] != null) {
                if (String(marker[textKey]).length > 0) {
                    return createTooltipTextRow(
                        String(marker[textKey]),
                        TOOLTIP_BODY_SIZE,
                        TOOLTIP_TEXT_COLOR,
                        false
                    );
                }
            }

            return null;
        }

        private static function createTooltipProgressRows(rows:Array):Array {
            // Lay the label / percent / status cells out as separate measured fields with
            // pixel-computed, right-aligned columns. Character-count space padding only
            // aligns in the embedded monospace font; translations outside its unicode
            // range (e.g. Cyrillic) render in the proportional fallback font and would
            // drift apart as label lengths diverge.
            var rowData:Object;
            var entry:Object;
            var entries:Array = [];
            var built:Array = [];
            var row:Sprite;
            var rowHeight:Number;
            var labelColumnWidth:Number = 0;
            var percentColumnWidth:Number = 0;
            var statusColumnWidth:Number = 0;

            for each (rowData in rows) {
                if (rowData == null) {
                    continue;
                }

                entry = {
                    labelField: makeTooltipRowField(String(rowData.labelText), TOOLTIP_BODY_SIZE, TOOLTIP_MUTED_TEXT_COLOR, false),
                    percentField: makeTooltipHtmlRowField(
                        buildTooltipStyledHtml(String(rowData.percentText), TOOLTIP_HIGHLIGHT_TEXT_COLOR, true, false),
                        TOOLTIP_BODY_SIZE,
                        TOOLTIP_HIGHLIGHT_TEXT_COLOR,
                        false
                    ),
                    statusField: makeTooltipHtmlRowField(String(rowData.statusHtml), TOOLTIP_BODY_SIZE, TOOLTIP_TEXT_COLOR, false)
                };
                labelColumnWidth = Math.max(labelColumnWidth, entry.labelField.width);
                percentColumnWidth = Math.max(percentColumnWidth, entry.percentField.width);
                statusColumnWidth = Math.max(statusColumnWidth, entry.statusField.width);
                entries.push(entry);
            }

            for each (entry in entries) {
                row = new Sprite();
                entry.labelField.x = labelColumnWidth - entry.labelField.width;
                entry.percentField.x = labelColumnWidth + TOOLTIP_PROGRESS_GAP + (percentColumnWidth - entry.percentField.width);
                entry.statusField.x = labelColumnWidth + TOOLTIP_PROGRESS_GAP + percentColumnWidth + TOOLTIP_PROGRESS_GAP
                    + (statusColumnWidth - entry.statusField.width);
                row.addChild(entry.labelField);
                row.addChild(entry.percentField);
                row.addChild(entry.statusField);

                rowHeight = Math.max(entry.labelField.height, Math.max(entry.percentField.height, entry.statusField.height));
                entry.labelField.y = Math.round((rowHeight - entry.labelField.height) / 2);
                entry.percentField.y = Math.round((rowHeight - entry.percentField.height) / 2);
                entry.statusField.y = Math.round((rowHeight - entry.statusField.height) / 2);
                built.push(row);
            }

            return built;
        }

        private static function createTooltipTitleCostRow(marker:Object, costXp:Number, combatXp:Number, freeXp:Number):Sprite {
            var row:Sprite = new Sprite();
            var icon:Sprite = null;
            var tooltipIconSize:Number = resolveMarkerTooltipIconSize(marker);
            var tooltipIconLayoutWidth:Number = Math.max(TOOLTIP_ICON_LAYOUT_WIDTH, tooltipIconSize);
            var titleField:TextField = makeTooltipRowField(resolveMarkerTooltipTitle(marker), TOOLTIP_TITLE_SIZE, TOOLTIP_TEXT_COLOR, true);
            var costField:TextField = makeTooltipHtmlRowField(
                buildTooltipHighlightedHtml("", formatExactXpValue(costXp), " XP", true),
                TOOLTIP_BODY_SIZE,
                TOOLTIP_MUTED_TEXT_COLOR,
                false
            );
            var rowHeight:Number;
            var titleX:Number = 0;

            if (!shouldHideTooltipIcon(marker)) {
                // Tint the title icon to the marker's state, matching its bar marker.
                icon = createTooltipMarkerIconForMarker(
                    marker,
                    tooltipIconSize,
                    tooltipIconLayoutWidth,
                    int(ResearchProgressBarIconTint.colorForMarker(marker, costXp, combatXp, freeXp))
                );
            }

            if (icon != null) {
                row.addChild(icon);
                titleX = tooltipIconLayoutWidth + TOOLTIP_ICON_GAP;
            }

            titleField.x = titleX;
            row.addChild(titleField);

            costField.x = titleField.x + titleField.width + TOOLTIP_PROGRESS_GAP;
            row.addChild(costField);

            // The title row stays a single line (icon + title + cost) so the icon lines up with the
            // title alone. The marker subtitle/name is rendered as its own row below (see
            // createTooltipSubtitleRow), matching how descriptions sit below in the other modes.
            rowHeight = Math.max(icon != null ? tooltipIconSize : 0, Math.max(titleField.height, costField.height));
            if (icon != null) {
                icon.y = Math.round((rowHeight - tooltipIconSize) / 2);
            }
            titleField.y = Math.round((rowHeight - titleField.height) / 2);
            costField.y = Math.round((rowHeight - costField.height) / 2);

            return row;
        }

        private static function createTooltipSubtitleRow(marker:Object):Sprite {
            var subtitleText:String = resolveMarkerTooltipSubtitle(marker);
            if (subtitleText.length == 0) {
                return null;
            }

            return createTooltipHtmlTextRow(subtitleText, TOOLTIP_SUBTITLE_SIZE, TOOLTIP_TEXT_COLOR, false);
        }

        private static function isEliteMarker(marker:Object):Boolean {
            var markerId:String;

            if (marker == null || marker.id === undefined || marker.id == null) {
                return false;
            }

            markerId = String(marker.id);
            return markerId.indexOf("elite_") == 0;
        }

        private static function resolveMarkerTooltipTitle(marker:Object):String {
            var markerName:String = ResearchProgressBarMarkerAssets.resolveMarkerName(marker);
            var levelValue:*;

            if (marker != null && marker.tooltipTitle !== undefined && marker.tooltipTitle != null && String(marker.tooltipTitle).length > 0) {
                return String(marker.tooltipTitle);
            }

            if (!isEliteMarker(marker) || marker == null || marker.level === undefined || marker.level == null) {
                return markerName;
            }

            levelValue = marker.level;
            return "Level " + String(levelValue) + ": " + markerName;
        }

        private static function resolveMarkerTooltipSubtitle(marker:Object):String {
            if (marker != null && marker.tooltipSubtitle !== undefined && marker.tooltipSubtitle != null && String(marker.tooltipSubtitle).length > 0) {
                return String(marker.tooltipSubtitle);
            }

            return "";
        }

        private static function resolveMarkerTooltipIconSize(marker:Object):Number {
            return TOOLTIP_ICON_SIZE;
        }

        private static function createTooltipIconTextRow(itemType:String, text:String, size:int, color:uint, bold:Boolean, iconSize:Number = TOOLTIP_ICON_SIZE, iconTintColor:int = -1):Sprite {
            var row:Sprite = new Sprite();
            // Icon tint defaults to the row's text colour, but callers can override it
            // (prerequisite rows tint their icons to the locked-grey state instead).
            var icon:Sprite = createTooltipMarkerIcon(itemType, iconSize, TOOLTIP_ICON_LAYOUT_WIDTH, iconTintColor >= 0 ? iconTintColor : int(color));
            var field:TextField = makeTooltipRowField(text, size, color, bold);
            var rowHeight:Number;

            if (icon != null) {
                row.addChild(icon);
            }

            field.x = icon != null ? TOOLTIP_ICON_LAYOUT_WIDTH + TOOLTIP_ICON_GAP : 0;
            row.addChild(field);

            rowHeight = Math.max(icon != null ? iconSize : 0, field.height);
            if (icon != null) {
                icon.y = Math.round((rowHeight - iconSize) / 2);
            }
            field.y = Math.round((rowHeight - field.height) / 2);
            return row;
        }

        private static function createTooltipTextRow(text:String, size:int, color:uint, bold:Boolean):Sprite {
            var row:Sprite = new Sprite();
            var field:TextField = makeTooltipRowField(text, size, color, bold);
            row.addChild(field);
            return row;
        }

        private static function createTooltipHtmlTextRow(html:String, size:int, color:uint, bold:Boolean):Sprite {
            var row:Sprite = new Sprite();
            var field:TextField = makeTooltipHtmlRowField(html, size, color, bold);
            row.addChild(field);
            return row;
        }

        private static function createTooltipMarkerIcon(itemType:String, iconSize:Number = TOOLTIP_ICON_SIZE, layoutWidth:Number = TOOLTIP_ICON_LAYOUT_WIDTH, tintColor:int = -1):Sprite {
            var iconSprite:Sprite = new Sprite();
            var bitmapData:BitmapData = ResearchProgressBarMarkerAssets.getMarkerIconBitmapData(itemType);
            var iconBitmap:Bitmap;

            if (bitmapData == null) {
                return null;
            }

            iconBitmap = new Bitmap(bitmapData);
            iconBitmap.smoothing = true;
            if (tintColor >= 0 && ResearchProgressBarMarkerAssets.isIconTypeTintable(itemType)) {
                ResearchProgressBarIconTint.applyColor(iconBitmap, uint(tintColor));
            }
            iconBitmap.x = 0;
            iconBitmap.y = 0;
            iconSprite.addChild(iconBitmap);
            return iconSprite;
        }

        private static function createTooltipMarkerIconForMarker(marker:Object, iconSize:Number = TOOLTIP_ICON_SIZE, layoutWidth:Number = TOOLTIP_ICON_LAYOUT_WIDTH, tintColor:int = -1):Sprite {
            var iconSprite:Sprite = new Sprite();
            var bitmapData:BitmapData = ResearchProgressBarMarkerAssets.getMarkerIconBitmapDataForMarker(marker);
            var iconBitmap:Bitmap;

            if (bitmapData == null) {
                return null;
            }

            iconBitmap = new Bitmap(bitmapData);
            iconBitmap.smoothing = true;
            if (tintColor >= 0 && ResearchProgressBarMarkerAssets.isMarkerBarIconTintable(marker)) {
                ResearchProgressBarIconTint.applyColor(iconBitmap, uint(tintColor));
            }
            iconBitmap.x = 0;
            iconBitmap.y = 0;
            iconSprite.addChild(iconBitmap);
            return iconSprite;
        }

        private static function makeTooltipRowField(text:String, size:int, color:uint, bold:Boolean):TextField {
            var field:TextField = makeTextField(color, size, bold);
            ResearchProgressBarFonts.setText(field, text);
            field.width = field.textWidth + 6;
            field.height = field.textHeight + TOOLTIP_TEXT_FIELD_PADDING;
            return field;
        }

        private static function makeTooltipHtmlRowField(html:String, size:int, color:uint, bold:Boolean):TextField {
            var field:TextField = makeTextField(color, size, bold);
            field.multiline = true;
            field.wordWrap = false;
            ResearchProgressBarFonts.setHtmlText(field, html);
            field.width = field.textWidth + 6;
            field.height = field.textHeight + TOOLTIP_TEXT_FIELD_PADDING;
            return field;
        }

        private static function buildTooltipProgressRowData(label:String, currentXp:Number, targetXp:Number, readyText:String, xpLeftFormat:String):Object {
            var pct:int;
            var missingXp:Number;
            var missingXpText:String;
            var statusText:String;
            var statusHtml:String;

            if (readyText == null || readyText.length == 0) {
                readyText = "ready for research";
            }
            if (xpLeftFormat == null || xpLeftFormat.length == 0) {
                xpLeftFormat = "{xp} XP left";
            }

            if (targetXp <= 0) {
                pct = 100;
                missingXp = 0;
            }
            else {
                pct = int(Math.min(100, currentXp * 100 / targetXp));
                missingXp = Math.max(0, targetXp - currentXp);
            }

            if (missingXp <= 0) {
                statusText = readyText;
                statusHtml = escapeHtml(statusText);
            }
            else {
                missingXpText = formatExactXpValue(missingXp);
                statusText = formatTooltipProgressText(xpLeftFormat, missingXpText);
                statusHtml = buildTooltipProgressFormatHtml(xpLeftFormat, missingXpText);
            }

            return {
                labelText: label,
                percentText: pct.toString() + "%",
                statusText: statusText,
                statusHtml: statusHtml
            };
        }

        private static function formatTooltipProgressText(format:String, xpText:String):String {
            if (format == null || format.length == 0) {
                format = "{xp} XP left";
            }

            if (format.indexOf("{xp}") < 0) {
                return xpText + " XP left";
            }

            return format.split("{xp}").join(xpText);
        }

        private static function buildTooltipProgressFormatHtml(format:String, xpText:String):String {
            var tokenIndex:int;
            var prefix:String;
            var suffix:String;

            if (format == null || format.length == 0) {
                format = "{xp} XP left";
            }

            tokenIndex = format.indexOf("{xp}");
            if (tokenIndex < 0) {
                return escapeHtml(formatTooltipProgressText(format, xpText));
            }

            prefix = format.substring(0, tokenIndex);
            suffix = format.substr(tokenIndex + 4);
            return buildTooltipHighlightedHtml(prefix, xpText, suffix, true);
        }

        private static function buildTooltipStyledHtml(text:String, color:uint, bold:Boolean, preserveSpaces:Boolean):String {
            var html:String = "<font color='#" + formatHtmlColor(color) + "'>";

            if (bold) {
                html += "<b>";
            }
            html += preserveSpaces ? escapeHtmlWithNbsp(text) : escapeHtml(text);
            if (bold) {
                html += "</b>";
            }
            html += "</font>";
            return html;
        }

        private static function buildTooltipHighlightedHtml(prefix:String, highlightedText:String, suffix:String, highlightBold:Boolean):String {
            var html:String = escapeHtml(prefix);

            html += "<font color='#" + formatHtmlColor(TOOLTIP_HIGHLIGHT_TEXT_COLOR) + "'>";
            if (highlightBold) {
                html += "<b>";
            }
            html += escapeHtml(highlightedText);
            if (highlightBold) {
                html += "</b>";
            }
            html += "</font>";
            html += escapeHtml(suffix);
            return html;
        }

        private static function createBlueprintTooltipRow(marker:Object):Sprite {
            var blueprintCount:int;
            var blueprintTotal:int;
            var blueprintDiscountPercent:int;
            var blueprintTooltipText:String;

            if (marker == null || marker.itemType !== "vehicle") {
                return null;
            }

            blueprintTotal = int(marker.blueprintTotal);
            if (blueprintTotal <= 0) {
                return null;
            }

            blueprintCount = int(marker.blueprintCount);
            blueprintDiscountPercent = int(marker.blueprintDiscountPercent);
            blueprintTooltipText = marker.blueprintTooltipText !== undefined && marker.blueprintTooltipText != null
                ? String(marker.blueprintTooltipText)
                : null;

            return createTooltipHtmlTextRow(
                buildBlueprintTooltipHtml(
                    blueprintCount,
                    blueprintTotal,
                    blueprintDiscountPercent,
                    blueprintTooltipText
                ),
                TOOLTIP_BODY_SIZE,
                TOOLTIP_MUTED_TEXT_COLOR,
                false
            );
        }

        private static function buildBlueprintTooltipHtml(
            blueprintCount:int,
            blueprintTotal:int,
            blueprintDiscountPercent:int,
            localizedText:String
        ):String {
            if (localizedText != null && localizedText.length > 0) {
                return buildLocalizedTooltipHighlightHtml(localizedText);
            }

            return buildTooltipHighlightedHtml("", blueprintCount.toString(), "/", true)
                + buildTooltipHighlightedHtml("", blueprintTotal.toString(), " Blueprints (", true)
                + buildTooltipHighlightedHtml("", blueprintDiscountPercent.toString() + "%", " discount)", true);
        }

        private static function buildLocalizedTooltipHighlightHtml(text:String):String {
            var html:String = "";
            var cursor:int = 0;
            var tagStart:int;
            var plainText:String;
            var tagName:String;
            var closeTag:String;
            var contentStart:int;
            var tagEnd:int;
            var highlightText:String;

            while (cursor < text.length) {
                tagStart = text.indexOf("<", cursor);
                if (tagStart < 0) {
                    html += escapeHtml(text.substr(cursor));
                    break;
                }

                plainText = text.substring(cursor, tagStart);
                if (plainText.length > 0) {
                    html += escapeHtml(plainText);
                }

                if (text.indexOf("<count>", tagStart) == tagStart) {
                    tagName = "count";
                }
                else if (text.indexOf("<total>", tagStart) == tagStart) {
                    tagName = "total";
                }
                else if (text.indexOf("<discount>", tagStart) == tagStart) {
                    tagName = "discount";
                }
                else {
                    html += escapeHtml(text.substr(tagStart, 1));
                    cursor = tagStart + 1;
                    continue;
                }

                closeTag = "</" + tagName + ">";
                contentStart = tagStart + tagName.length + 2;
                tagEnd = text.indexOf(closeTag, contentStart);
                if (tagEnd < 0) {
                    html += escapeHtml(text.substr(tagStart));
                    break;
                }

                highlightText = text.substring(contentStart, tagEnd);
                html += buildTooltipHighlightedHtml("", highlightText, "", true);
                cursor = tagEnd + closeTag.length;
            }

            return html;
        }

        private static function escapeHtml(text:String):String {
            if (text == null) {
                return "";
            }

            return text.split("&").join("&amp;").split("<").join("&lt;").split(">").join("&gt;");
        }

        private static function escapeHtmlWithNbsp(text:String):String {
            return escapeHtml(text).split(" ").join("&nbsp;");
        }

        private static function formatHtmlColor(color:uint):String {
            var hex:String = color.toString(16).toUpperCase();

            while (hex.length < 6) {
                hex = "0" + hex;
            }

            return hex;
        }

        private static function resolveTooltipItemLabel(item:Object):String {
            if (item != null && item.name !== undefined && item.name != null && String(item.name).length > 0) {
                return String(item.name);
            }

            if (item != null && item.item_type !== undefined) {
                return ResearchProgressBarMarkerAssets.resolveMarkerName({itemType: item.item_type});
            }

            return ResearchProgressBarMarkerAssets.resolveMarkerName(null);
        }

        private static function shouldHideTooltipIcon(marker:Object):Boolean {
            return marker != null && marker.hideTooltipIcon !== undefined && Boolean(marker.hideTooltipIcon);
        }

        private static function formatExactXpValue(value:Number):String {
            var integerValue:int = Math.round(value);
            var text:String = Math.abs(integerValue).toString();
            var parts:Array = [];

            while (text.length > 3) {
                parts.unshift(text.substr(text.length - 3));
                text = text.substr(0, text.length - 3);
            }

            if (text.length > 0) {
                parts.unshift(text);
            }

            text = parts.join(" ");
            if (integerValue < 0) {
                text = "-" + text;
            }

            return text;
        }

        private static function ltrim(text:String):String {
            if (text == null) {
                return "";
            }

            while (text.length > 0 && text.charAt(0) == " ") {
                text = text.substr(1);
            }

            return text;
        }

        private static function rtrim(text:String):String {
            if (text == null) {
                return "";
            }

            while (text.length > 0 && text.charAt(text.length - 1) == " ") {
                text = text.substr(0, text.length - 1);
            }

            return text;
        }

        private static function makeTextField(color:uint, size:int, bold:Boolean):TextField {
            var field:TextField = ResearchProgressBarFonts.configureTextField(new TextField());
            field.defaultTextFormat = new TextFormat(TOOLTIP_FONT_NAME, size, color, bold);
            field.selectable = false;
            field.mouseEnabled = false;
            field.textColor = color;
            field.multiline = false;
            field.wordWrap = false;
            return field;
        }
    }
}