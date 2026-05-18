package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.Sprite;
    import flash.text.TextField;
    import flash.text.TextFormat;
    import flash.text.TextFormatAlign;

    public final class ResearchProgressBarTooltipContent {
        public static const SECTION_GAP:Number = 10;

        private static const TOOLTIP_TEXT_COLOR:uint = 0xE6DDC8;
        private static const TOOLTIP_MUTED_TEXT_COLOR:uint = 0xB8AC97;
        private static const TOOLTIP_HIGHLIGHT_TEXT_COLOR:uint = 0xF0CF74;
        private static const TOOLTIP_ICON_SIZE:Number = 20;
        private static const TOOLTIP_COMPACT_ICON_SIZE:Number = TOOLTIP_ICON_SIZE;
        private static const TOOLTIP_ICON_LAYOUT_WIDTH:Number = TOOLTIP_ICON_SIZE;
        private static const TOOLTIP_ICON_GAP:Number = 6;
        private static const TOOLTIP_ROW_GAP:Number = 3;
        private static const TOOLTIP_COMPACT_ROW_GAP:Number = 1;
        private static const TOOLTIP_TITLE_SIZE:int = 13;
        private static const TOOLTIP_BODY_SIZE:int = 12;
        private static const TOOLTIP_PROGRESS_LABEL_WIDTH:Number = 68;
        private static const TOOLTIP_PROGRESS_PERCENT_WIDTH:Number = 40;
        private static const TOOLTIP_PROGRESS_GAP:Number = 8;

        public static function buildTooltipSection(entry:Object):Sprite {
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
            var singleProgressRow:Boolean = marker != null && marker.singleProgressRow !== undefined && Boolean(marker.singleProgressRow);

            row = createTooltipTitleCostRow(marker, markerCostXp);
            row.y = cursorY;
            section.addChild(row);
            rowBounds = row.getBounds(row);
            cursorY += rowBounds.height + TOOLTIP_ROW_GAP;

            if (markerState == "completed") {
                row = createTooltipTextRow(
                    "Unlocked",
                    TOOLTIP_BODY_SIZE,
                    TOOLTIP_HIGHLIGHT_TEXT_COLOR,
                    true
                );
                row.y = cursorY;
                section.addChild(row);
                return section;
            }

            if (marker != null && marker.isAvailable !== undefined && !Boolean(marker.isAvailable)) {
                row = createTooltipTextRow(
                    "Prerequisites:",
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
                        TOOLTIP_COMPACT_ICON_SIZE
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
                    rowBounds = row.getBounds(row);
                    cursorY += rowBounds.height + TOOLTIP_ROW_GAP;
                }

                return section;
            }

            row = createTooltipProgressRow(progressLabel, combatXp, markerCostXp);
            row.y = cursorY;
            section.addChild(row);
            rowBounds = row.getBounds(row);
            cursorY += rowBounds.height + TOOLTIP_ROW_GAP;

            if (singleProgressRow) {
                return section;
            }

            row = createTooltipProgressRow("Total XP", combatXp + freeXp, markerCostXp);
            row.y = cursorY;
            section.addChild(row);

            return section;
        }

        public static function buildEliteStatusCounterHtml(text:String):String {
            var suffix:String = " Base XP";

            if (text == null) {
                return "";
            }

            if (text.length > suffix.length && text.substr(text.length - suffix.length) == suffix) {
                return buildTooltipHighlightedHtml("", text.substr(0, text.length - suffix.length), suffix, true);
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

        private static function createTooltipProgressRow(label:String, currentXp:Number, targetXp:Number):Sprite {
            var row:Sprite = new Sprite();
            var labelField:TextField;
            var percentField:TextField;
            var statusField:TextField;
            var pct:int;
            var missingXp:Number;
            var statusText:String;
            var rowHeight:Number;

            if (targetXp <= 0) {
                pct = 100;
                missingXp = 0;
            }
            else {
                pct = int(Math.min(100, currentXp * 100 / targetXp));
                missingXp = Math.max(0, targetXp - currentXp);
            }

            if (missingXp <= 0) {
                statusText = "ready for research";
                statusField = makeTooltipRowField(statusText, TOOLTIP_BODY_SIZE, TOOLTIP_TEXT_COLOR, false);
            }
            else {
                statusField = makeTooltipHtmlRowField(
                    buildTooltipHighlightedHtml("", formatExactXpValue(missingXp), " XP left", true),
                    TOOLTIP_BODY_SIZE,
                    TOOLTIP_TEXT_COLOR,
                    false
                );
            }

            labelField = makeTooltipRowField(label, TOOLTIP_BODY_SIZE, TOOLTIP_MUTED_TEXT_COLOR, false);
            labelField.width = TOOLTIP_PROGRESS_LABEL_WIDTH;
            alignTextField(labelField, TextFormatAlign.RIGHT);
            row.addChild(labelField);

            percentField = makeTooltipRowField(pct.toString() + "%", TOOLTIP_BODY_SIZE, TOOLTIP_HIGHLIGHT_TEXT_COLOR, true);
            percentField.width = TOOLTIP_PROGRESS_PERCENT_WIDTH;
            percentField.x = TOOLTIP_PROGRESS_LABEL_WIDTH + TOOLTIP_PROGRESS_GAP;
            alignTextField(percentField, TextFormatAlign.RIGHT);
            row.addChild(percentField);

            statusField.x = percentField.x + TOOLTIP_PROGRESS_PERCENT_WIDTH + TOOLTIP_PROGRESS_GAP;
            row.addChild(statusField);

            rowHeight = Math.max(labelField.height, Math.max(percentField.height, statusField.height));
            labelField.y = Math.round((rowHeight - labelField.height) / 2);
            percentField.y = Math.round((rowHeight - percentField.height) / 2);
            statusField.y = Math.round((rowHeight - statusField.height) / 2);
            return row;
        }

        private static function createTooltipTitleCostRow(marker:Object, costXp:Number):Sprite {
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
            var textBlockHeight:Number;
            var textBlockTop:Number;
            var titleX:Number = 0;

            if (!shouldHideTooltipIcon(marker)) {
                icon = createTooltipMarkerIconForMarker(marker, tooltipIconSize, tooltipIconLayoutWidth);
            }

            if (icon != null) {
                row.addChild(icon);
                titleX = tooltipIconLayoutWidth + TOOLTIP_ICON_GAP;
            }

            titleField.x = titleX;
            row.addChild(titleField);

            costField.x = titleField.x + titleField.width + TOOLTIP_PROGRESS_GAP;
            row.addChild(costField);

            rowHeight = Math.max(tooltipIconSize, Math.max(titleField.height, costField.height));
            if (icon != null) {
                icon.y = Math.round((rowHeight - tooltipIconSize) / 2);
            }
            textBlockHeight = Math.max(titleField.height, costField.height);
            textBlockTop = Math.round((rowHeight - textBlockHeight) / 2);
            titleField.y = textBlockTop + (textBlockHeight - titleField.height);
            costField.y = textBlockTop + (textBlockHeight - costField.height);

            return row;
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

            if (!isEliteMarker(marker) || marker == null || marker.level === undefined || marker.level == null) {
                return markerName;
            }

            levelValue = marker.level;
            return "Level " + String(levelValue) + ": " + markerName;
        }

        private static function resolveMarkerTooltipIconSize(marker:Object):Number {
            return TOOLTIP_ICON_SIZE;
        }

        private static function createTooltipIconTextRow(itemType:String, text:String, size:int, color:uint, bold:Boolean, iconSize:Number = TOOLTIP_ICON_SIZE):Sprite {
            var row:Sprite = new Sprite();
            var icon:Sprite = createTooltipMarkerIcon(itemType, iconSize);
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

        private static function createTooltipMarkerIcon(itemType:String, iconSize:Number = TOOLTIP_ICON_SIZE, layoutWidth:Number = TOOLTIP_ICON_LAYOUT_WIDTH):Sprite {
            var iconSprite:Sprite = new Sprite();
            var bitmapData:BitmapData = ResearchProgressBarMarkerAssets.getMarkerIconBitmapData(itemType);
            var iconBitmap:Bitmap;

            if (bitmapData == null) {
                return null;
            }

            iconBitmap = new Bitmap(bitmapData);
            iconBitmap.smoothing = true;
            iconBitmap.x = 0;
            iconBitmap.y = 0;
            iconSprite.addChild(iconBitmap);
            return iconSprite;
        }

        private static function createTooltipMarkerIconForMarker(marker:Object, iconSize:Number = TOOLTIP_ICON_SIZE, layoutWidth:Number = TOOLTIP_ICON_LAYOUT_WIDTH):Sprite {
            var iconSprite:Sprite = new Sprite();
            var bitmapData:BitmapData = ResearchProgressBarMarkerAssets.getMarkerIconBitmapDataForMarker(marker);
            var iconBitmap:Bitmap;

            if (bitmapData == null) {
                return null;
            }

            iconBitmap = new Bitmap(bitmapData);
            iconBitmap.smoothing = true;
            iconBitmap.x = 0;
            iconBitmap.y = 0;
            iconSprite.addChild(iconBitmap);
            return iconSprite;
        }

        private static function makeTooltipRowField(text:String, size:int, color:uint, bold:Boolean):TextField {
            var field:TextField = makeTextField(color, size, bold);
            field.text = text;
            field.width = field.textWidth + 6;
            field.height = field.textHeight + 6;
            return field;
        }

        private static function makeTooltipHtmlRowField(html:String, size:int, color:uint, bold:Boolean):TextField {
            var field:TextField = makeTextField(color, size, bold);
            field.htmlText = html;
            field.width = field.textWidth + 6;
            field.height = field.textHeight + 6;
            return field;
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

        private static function escapeHtml(text:String):String {
            if (text == null) {
                return "";
            }

            return text.split("&").join("&amp;").split("<").join("&lt;").split(">").join("&gt;");
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

        private static function alignTextField(field:TextField, alignment:String):void {
            var format:TextFormat = field.defaultTextFormat;

            format.align = alignment;
            field.defaultTextFormat = format;
            field.setTextFormat(format);
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

        private static function makeTextField(color:uint, size:int, bold:Boolean):TextField {
            var field:TextField = new TextField();
            field.defaultTextFormat = new TextFormat("_sans", size, color, bold);
            field.selectable = false;
            field.mouseEnabled = false;
            field.textColor = color;
            field.multiline = false;
            field.wordWrap = false;
            return field;
        }
    }
}