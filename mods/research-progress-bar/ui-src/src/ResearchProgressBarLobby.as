package
{
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.Loader;
    import flash.display.Shape;
    import flash.display.Sprite;
    import flash.events.Event;
    import flash.events.IOErrorEvent;
    import flash.events.MouseEvent;
    import flash.geom.Rectangle;
    import flash.net.URLRequest;
    import flash.text.TextField;
    import flash.text.TextFormat;
    import flash.text.TextFormatAlign;
    import flash.utils.Dictionary;
    import net.wg.infrastructure.base.AbstractView;

    [SWF(width="1920", height="220", frameRate="30", backgroundColor="#000000")]
    public class ResearchProgressBarLobby extends AbstractView
    {
        [Embed(source="../assets/progress_bar_base.png")]
        private static const ProgressBarBaseAsset:Class;

        [Embed(source="../assets/progress_bar_green.png")]
        private static const ProgressBarGreenAsset:Class;

        [Embed(source="../assets/progress_bar_yellow.png")]
        private static const ProgressBarYellowAsset:Class;

        [Embed(source="../assets/marker_default.png")]
        private static const MarkerDefaultAsset:Class;

        [Embed(source="../assets/marker_green.png")]
        private static const MarkerGreenAsset:Class;

        [Embed(source="../assets/marker_yellow.png")]
        private static const MarkerYellowAsset:Class;

        private static const SIDE_MARGIN:Number = 600;
        private static const TOP_MARGIN:Number = 105;
        private static const MIN_BAR_WIDTH:Number = 80;
        private static const BAR_HEIGHT:Number = 8;
        private static const LABEL_COLOR:uint = 0xE6DDC8;
        private static const COUNTER_GAP:Number = 14;
        private static const COUNTER_VALUE_WIDTH:Number = 44;
        private static const COUNTER_TEXT_GAP:Number = 5;
        private static const COUNTER_CAPTION_WIDTH:Number = 84;
        private static const MARKER_VALUE_COLOR:uint = 0xB8AC97;
        private static const MARKER_ICON_SIZE:Number = 48;
        private static const MARKER_ICON_Y_OFFSET:Number = 7;
        private static const TOOLTIP_BACKGROUND_COLOR:uint = 0x0B0B0B;
        private static const TOOLTIP_BACKGROUND_ALPHA:Number = 0.93;
        private static const TOOLTIP_BORDER_COLOR:uint = 0x7A6954;
        private static const TOOLTIP_TEXT_COLOR:uint = 0xE6DDC8;
        private static const TOOLTIP_MUTED_TEXT_COLOR:uint = 0xB8AC97;
        private static const TOOLTIP_HIGHLIGHT_TEXT_COLOR:uint = 0xF0CF74;
        private static const TOOLTIP_PADDING_X:Number = 8;
        private static const TOOLTIP_PADDING_Y:Number = 6;
        private static const TOOLTIP_PADDING_BOTTOM:Number = 8;
        private static const TOOLTIP_OFFSET_Y:Number = 10;
        private static const TOOLTIP_ICON_SIZE:Number = MARKER_ICON_SIZE;
        private static const TOOLTIP_COMPACT_ICON_SIZE:Number = 32;
        private static const TOOLTIP_ICON_LAYOUT_WIDTH:Number = 18;
        private static const TOOLTIP_ICON_GAP:Number = 6;
        private static const TOOLTIP_ROW_GAP:Number = 3;
        private static const TOOLTIP_COMPACT_ROW_GAP:Number = 1;
        private static const TOOLTIP_SECTION_GAP:Number = 10;
        private static const TOOLTIP_TITLE_SIZE:int = 13;
        private static const TOOLTIP_BODY_SIZE:int = 12;
        private static const TOOLTIP_PROGRESS_LABEL_WIDTH:Number = 68;
        private static const TOOLTIP_PROGRESS_PERCENT_WIDTH:Number = 40;
        private static const TOOLTIP_PROGRESS_GAP:Number = 8;
        private static const MARKER_TYPE_NAMES:Object = {
            gun: "Gun",
            turret: "Turret",
            engine: "Engine",
            suspension: "Suspension",
            radio: "Radio",
            vehicle: "Next Vehicle",
            unknown: "Research Item"
        };
        private static const MARKER_ICON_PATHS:Object = {
            gun: [
                "../maps/icons/hangar/vehicleMenu/small/research_gun.png",
                "img://gui/maps/icons/hangar/vehicleMenu/small/research_gun.png"
            ],
            turret: [
                "../maps/icons/hangar/vehicleMenu/small/research_turret.png",
                "img://gui/maps/icons/hangar/vehicleMenu/small/research_turret.png"
            ],
            engine: [
                "../maps/icons/hangar/vehicleMenu/small/research_engine.png",
                "img://gui/maps/icons/hangar/vehicleMenu/small/research_engine.png"
            ],
            suspension: [
                "../maps/icons/hangar/vehicleMenu/small/research_track.png",
                "img://gui/maps/icons/hangar/vehicleMenu/small/research_track.png"
            ],
            radio: [
                "../maps/icons/hangar/vehicleMenu/small/research_radio.png",
                "img://gui/maps/icons/hangar/vehicleMenu/small/research_radio.png"
            ],
            vehicle: [
                "../maps/icons/hangar/vehicleMenu/small/research.png",
                "img://gui/maps/icons/hangar/vehicleMenu/small/research.png"
            ]
        };

        private var combatPercentLabel:TextField;
        private var combatPercentCaption:TextField;
        private var totalPercentLabel:TextField;
        private var totalPercentCaption:TextField;
        private var baseBar:Bitmap;
        private var combatBar:Bitmap;
        private var freeBar:Bitmap;
        private var combatMaskShape:Shape;
        private var freeMaskShape:Shape;
        private var markersContainer:Sprite;
        private var tooltipContainer:Sprite;
        private var tooltipBackground:Shape;
        private var tooltipContent:Sprite;
        private var _context:Object;
        private var _barWidth:Number = MIN_BAR_WIDTH;
        private var _isReady:Boolean = false;
        private var _markerIconBitmapByType:Object = {};
        private var _markerIconLoadStateByType:Object = {};
        private var _markerTooltipDataByDisplay:Dictionary = new Dictionary(true);

        public function ResearchProgressBarLobby()
        {
            super();
        }

        override protected function configUI():void
        {
            super.configUI();
            mouseEnabled = false;
            mouseChildren = true;
            build();

            if (stage != null)
            {
                stage.addEventListener(Event.RESIZE, onStageResize);
                stage.addEventListener(MouseEvent.MOUSE_MOVE, onStageMouseMove, false, 0, true);
                stage.addEventListener(Event.MOUSE_LEAVE, onStageMouseLeave, false, 0, true);
            }
        }

        override protected function onDispose():void
        {
            hideMarkerTooltip();
            if (stage != null)
            {
                stage.removeEventListener(Event.RESIZE, onStageResize);
                stage.removeEventListener(MouseEvent.MOUSE_MOVE, onStageMouseMove);
                stage.removeEventListener(Event.MOUSE_LEAVE, onStageMouseLeave);
            }
            super.onDispose();
        }

        override protected function nextFrameAfterPopulateHandler():void
        {
            super.nextFrameAfterPopulateHandler();
            _isReady = true;
            layoutFromStage();
            updateBarFromContext();
        }

        private function build():void
        {
            combatPercentLabel = makeCounterField();
            addChild(combatPercentLabel);

            combatPercentCaption = makeCounterCaptionField("Vehicle XP");
            addChild(combatPercentCaption);

            totalPercentLabel = makeCounterField();
            addChild(totalPercentLabel);

            totalPercentCaption = makeCounterCaptionField("Total XP");
            addChild(totalPercentCaption);

            baseBar = createBitmap(ProgressBarBaseAsset);
            addChild(baseBar);

            combatBar = createBitmap(ProgressBarGreenAsset);
            addChild(combatBar);

            freeBar = createBitmap(ProgressBarYellowAsset);
            addChild(freeBar);

            combatMaskShape = new Shape();
            combatMaskShape.visible = false;
            addChild(combatMaskShape);

            freeMaskShape = new Shape();
            freeMaskShape.visible = false;
            addChild(freeMaskShape);

            combatBar.mask = combatMaskShape;
            freeBar.mask = freeMaskShape;

            markersContainer = new Sprite();
            markersContainer.mouseEnabled = false;
            addChild(markersContainer);

            tooltipContainer = new Sprite();
            tooltipContainer.mouseEnabled = false;
            tooltipContainer.mouseChildren = false;
            tooltipContainer.visible = false;

            tooltipBackground = new Shape();
            tooltipContainer.addChild(tooltipBackground);

            tooltipContent = new Sprite();
            tooltipContent.mouseEnabled = false;
            tooltipContent.mouseChildren = false;
            tooltipContainer.addChild(tooltipContent);

            addChild(tooltipContainer);
        }

        private function onStageResize(event:Event):void
        {
            layoutFromStage();
            updateBarFromContext();
        }

        private function onStageMouseMove(event:MouseEvent):void
        {
            updateTooltipAtStagePoint(event.stageX, event.stageY);
        }

        private function onStageMouseLeave(event:Event):void
        {
            hideMarkerTooltip();
        }

        public function as_setContext(data:Object):void
        {
            applyContext(data);
        }

        public function as_setProgress(value:Number):void
        {
            if (_context == null)
            {
                _context = {};
            }
            _context.progress = Number(value);
            if (_isReady)
            {
                updateBarFromContext();
            }
        }

        public function as_ping():String
        {
            return "research-progress-bar-lobby-ready";
        }

        public function as_setVisible(value:Boolean):void
        {
            visible = value;
            if (!value)
            {
                hideMarkerTooltip();
            }
        }

        private function applyContext(data:Object):void
        {
            if (data == null)
            {
                return;
            }

            _context = data;

            if (!_isReady)
            {
                return;
            }

            layoutFromStage();
            updateBarFromContext();
        }

        private function updateBarFromContext():void
        {
            var maxRequirementXp:Number;
            var combatXp:Number;
            var freeXp:Number;
            var combatWidth:Number;
            var freeWidth:Number;
            var combatPercent:int;
            var totalPercent:int;

            if (!_isReady || _context == null)
            {
                return;
            }

            if (baseBar == null || combatBar == null || freeBar == null || markersContainer == null)
            {
                return;
            }

            layoutFromStage();

            maxRequirementXp = Math.max(1, numberValue(_context.maxRequirementXp, 1));
            combatXp = clamp(numberValue(_context.combatXp, 0), 0, maxRequirementXp);
            freeXp = clamp(numberValue(_context.freeXp, 0), 0, maxRequirementXp - combatXp);
            combatWidth = Math.round(_barWidth * combatXp / maxRequirementXp);
            freeWidth = Math.round(_barWidth * freeXp / maxRequirementXp);

            combatPercent = int(Math.min(100, combatXp * 100 / maxRequirementXp));
            totalPercent = int(Math.min(100, (combatXp + freeXp) * 100 / maxRequirementXp));
            combatPercentLabel.text = combatPercent.toString() + "%";
            totalPercentLabel.text = totalPercent.toString() + "%";

            baseBar.x = SIDE_MARGIN;
            baseBar.y = TOP_MARGIN;
            baseBar.width = _barWidth;
            baseBar.height = BAR_HEIGHT;

            combatBar.x = SIDE_MARGIN;
            combatBar.y = TOP_MARGIN;
            combatBar.width = _barWidth;
            combatBar.height = BAR_HEIGHT;

            freeBar.x = SIDE_MARGIN;
            freeBar.y = TOP_MARGIN;
            freeBar.width = _barWidth;
            freeBar.height = BAR_HEIGHT;

            drawMask(combatMaskShape, SIDE_MARGIN, TOP_MARGIN, combatWidth, BAR_HEIGHT);
            drawMask(freeMaskShape, SIDE_MARGIN + combatWidth, TOP_MARGIN, freeWidth, BAR_HEIGHT);

            rebuildMarkers(maxRequirementXp, combatXp, freeXp);
            positionLabels();
        }

        private function rebuildMarkers(maxRequirementXp:Number, combatXp:Number, freeXp:Number):void
        {
            var marker:Object;
            var markerCostXp:Number;
            var markerX:Number;
            var markerDisplay:Sprite;

            hideMarkerTooltip();
            _markerTooltipDataByDisplay = new Dictionary(true);

            while (markersContainer.numChildren > 0)
            {
                markersContainer.removeChildAt(0);
            }

            if (!(_context.markers is Array))
            {
                return;
            }

            for each (marker in _context.markers)
            {
                markerCostXp = clamp(numberValue(marker.costXp, 0), 0, maxRequirementXp);
                markerX = Math.round(_barWidth * markerCostXp / maxRequirementXp);
                markerDisplay = createMarkerDisplay(marker, markerCostXp, combatXp, freeXp);
                markerDisplay.x = SIDE_MARGIN + markerX;
                markerDisplay.y = TOP_MARGIN;
                updateMarkerHitArea(markerDisplay);
                markersContainer.addChild(markerDisplay);
            }
        }

        private function createMarkerDisplay(marker:Object, markerCostXp:Number, combatXp:Number, freeXp:Number):Sprite
        {
            var markerSprite:Sprite = new Sprite();
            var markerBitmap:Bitmap = createMarkerBitmap(marker, markerCostXp, combatXp, freeXp);
            var markerIcon:Bitmap;
            var markerLabel:TextField;
            var markerLabelText:String = marker != null && marker.label !== undefined ? String(marker.label) : "";
            var markerItemType:String = marker != null && marker.itemType !== undefined ? String(marker.itemType) : "";

            markerBitmap.x = -Math.round(markerBitmap.width / 2);
            markerBitmap.y = -Math.round((markerBitmap.height - BAR_HEIGHT) / 2);
            markerSprite.addChild(markerBitmap);

            markerIcon = createMarkerIcon(markerItemType, markerBitmap.y);
            if (markerIcon != null)
            {
                markerSprite.addChild(markerIcon);
            }
            else if (markerLabelText.length > 0)
            {
                markerLabel = makeMarkerLabelField(markerLabelText, markerBitmap.y);
                markerSprite.addChild(markerLabel);
            }

            markerSprite.mouseEnabled = true;
            markerSprite.mouseChildren = false;
            markerSprite.addEventListener(MouseEvent.MOUSE_OVER, onMarkerMouseOver, false, 0, true);
            markerSprite.addEventListener(MouseEvent.MOUSE_OUT, onMarkerMouseOut, false, 0, true);
            _markerTooltipDataByDisplay[markerSprite] = {
                marker: marker,
                costXp: markerCostXp,
                combatXp: combatXp,
                freeXp: freeXp
            };

            return markerSprite;
        }

        private function updateMarkerHitArea(markerDisplay:Sprite):void
        {
            var bounds:Rectangle;

            if (markerDisplay == null)
            {
                return;
            }

            bounds = markerDisplay.getBounds(markerDisplay);
            if (bounds == null)
            {
                return;
            }

            markerDisplay.graphics.clear();
            markerDisplay.graphics.beginFill(0x000000, 0.0);
            markerDisplay.graphics.drawRect(bounds.x, bounds.y - 2, bounds.width, bounds.height + 4);
            markerDisplay.graphics.endFill();
        }

        private function createMarkerBitmap(marker:Object, markerCostXp:Number, combatXp:Number, freeXp:Number):Bitmap
        {
            if (marker != null && marker.isAvailable !== undefined && !Boolean(marker.isAvailable))
            {
                return createBitmap(MarkerDefaultAsset);
            }
            if (markerCostXp <= combatXp)
            {
                return createBitmap(MarkerGreenAsset);
            }
            if (markerCostXp <= combatXp + freeXp)
            {
                return createBitmap(MarkerYellowAsset);
            }
            return createBitmap(MarkerDefaultAsset);
        }

        private function onMarkerMouseOver(event:MouseEvent):void
        {
            updateTooltipAtStagePoint(event.stageX, event.stageY);
        }

        private function onMarkerMouseOut(event:MouseEvent):void
        {
            updateTooltipAtStagePoint(event.stageX, event.stageY);
        }

        private function updateTooltipAtStagePoint(stageX:Number, stageY:Number):void
        {
            var tooltipEntries:Array = [];
            var candidate:Sprite;
            var candidateBounds:Rectangle;
            var candidateData:Object;
            var idx:int;

            if (!visible || markersContainer == null)
            {
                hideMarkerTooltip();
                return;
            }

            for (idx = 0; idx < markersContainer.numChildren; idx++)
            {
                candidate = markersContainer.getChildAt(idx) as Sprite;
                if (candidate == null)
                {
                    continue;
                }

                candidateBounds = candidate.getBounds(stage);
                if (candidateBounds == null || !candidateBounds.contains(stageX, stageY))
                {
                    continue;
                }

                candidateData = _markerTooltipDataByDisplay[candidate];
                if (candidateData != null)
                {
                    tooltipEntries.push(candidateData);
                }
            }

            if (tooltipEntries.length == 0)
            {
                hideMarkerTooltip();
                return;
            }

            showTooltipEntries(tooltipEntries, stageX, stageY);
        }

        private function showTooltipEntries(entries:Array, stageX:Number, stageY:Number):void
        {
            var entry:Object;
            var section:Sprite;
            var sectionBounds:Rectangle;
            var contentBounds:Rectangle;
            var cursorY:Number = 0;
            var idx:int;
            var tooltipWidth:Number;
            var tooltipHeight:Number;

            if (tooltipContainer == null || tooltipContent == null || tooltipBackground == null)
            {
                return;
            }

            clearTooltipContent();

            for (idx = 0; idx < entries.length; idx++)
            {
                entry = entries[idx];
                section = buildTooltipSection(entry);
                section.y = cursorY;
                tooltipContent.addChild(section);
                sectionBounds = section.getBounds(section);
                cursorY += sectionBounds.height;
                if (idx < entries.length - 1)
                {
                    cursorY += TOOLTIP_SECTION_GAP;
                }
            }

            contentBounds = tooltipContent.getBounds(tooltipContent);
            tooltipContent.x = TOOLTIP_PADDING_X - contentBounds.x;
            tooltipContent.y = TOOLTIP_PADDING_Y - contentBounds.y;

            tooltipWidth = contentBounds.width + TOOLTIP_PADDING_X * 2;
            tooltipHeight = contentBounds.height + TOOLTIP_PADDING_Y + TOOLTIP_PADDING_BOTTOM;
            drawTooltipBackground(tooltipWidth, tooltipHeight);

            tooltipContainer.visible = true;
            positionTooltip(stageX, stageY, tooltipWidth, tooltipHeight);
        }

        private function clearTooltipContent():void
        {
            if (tooltipContent == null)
            {
                return;
            }

            while (tooltipContent.numChildren > 0)
            {
                tooltipContent.removeChildAt(0);
            }
        }

        private function hideMarkerTooltip():void
        {
            if (tooltipContainer != null)
            {
                tooltipContainer.visible = false;
            }
        }

        private function positionTooltip(stageX:Number, stageY:Number, tooltipWidth:Number, tooltipHeight:Number):void
        {
            var tooltipX:Number = stageX - Math.round(tooltipWidth / 2);
            var tooltipY:Number = stageY - tooltipHeight - TOOLTIP_OFFSET_Y;
            var minX:Number = 4;
            var maxX:Number;
            var minY:Number = 4;

            if (stage != null)
            {
                maxX = stage.stageWidth - tooltipWidth - 4;
                if (tooltipX < minX)
                {
                    tooltipX = minX;
                }
                if (tooltipX > maxX)
                {
                    tooltipX = maxX;
                }
            }

            if (tooltipY < minY)
            {
                tooltipY = stageY + TOOLTIP_OFFSET_Y;
            }

            tooltipContainer.x = Math.round(tooltipX);
            tooltipContainer.y = Math.round(tooltipY);
        }

        private function drawTooltipBackground(width:Number, height:Number):void
        {
            tooltipBackground.graphics.clear();
            tooltipBackground.graphics.lineStyle(1, TOOLTIP_BORDER_COLOR, 1.0);
            tooltipBackground.graphics.beginFill(TOOLTIP_BACKGROUND_COLOR, TOOLTIP_BACKGROUND_ALPHA);
            tooltipBackground.graphics.drawRoundRect(0, 0, width, height, 6, 6);
            tooltipBackground.graphics.endFill();
        }

        private function buildTooltipSection(entry:Object):Sprite
        {
            var section:Sprite = new Sprite();
            var marker:Object = entry.marker;
            var markerCostXp:Number = Number(entry.costXp);
            var combatXp:Number = Number(entry.combatXp);
            var freeXp:Number = Number(entry.freeXp);
            var row:Sprite;
            var rowBounds:Rectangle;
            var cursorY:Number = 0;
            var prereq:Object;
            var prereqs:Array;

            row = createTooltipTitleCostRow(marker, markerCostXp);
            row.y = cursorY;
            section.addChild(row);
            rowBounds = row.getBounds(row);
            cursorY += rowBounds.height + TOOLTIP_ROW_GAP;

            if (marker != null && marker.isAvailable !== undefined && !Boolean(marker.isAvailable))
            {
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
                for each (prereq in prereqs)
                {
                    row = createTooltipIconTextRow(
                        prereq != null && prereq.item_type !== undefined ? String(prereq.item_type) : "unknown",
                        prereq != null && prereq.label !== undefined ? String(prereq.label) : "?",
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

                if (prereqs.length == 0)
                {
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

            row = createTooltipProgressRow("Vehicle XP", combatXp, markerCostXp);
            row.y = cursorY;
            section.addChild(row);
            rowBounds = row.getBounds(row);
            cursorY += rowBounds.height + TOOLTIP_ROW_GAP;

            row = createTooltipProgressRow("Total XP", combatXp + freeXp, markerCostXp);
            row.y = cursorY;
            section.addChild(row);

            return section;
        }

        private function resolveLockedBehindText(marker:Object):String
        {
            var prereqNames:Array;
            var prereqText:String;

            if (marker != null && marker.missingPrereqNames is Array)
            {
                prereqNames = marker.missingPrereqNames as Array;
                if (prereqNames.length == 1)
                {
                    return "Prerequisites: " + String(prereqNames[0]);
                }
                if (prereqNames.length > 1)
                {
                    prereqText = prereqNames.join(", ");
                    return "Prerequisites: " + prereqText;
                }
            }

            return "Prerequisites missing";
        }

        private function createTooltipProgressRow(label:String, currentXp:Number, targetXp:Number):Sprite
        {
            var row:Sprite = new Sprite();
            var labelField:TextField;
            var percentField:TextField;
            var statusField:TextField;
            var pct:int = int(Math.min(100, currentXp * 100 / Math.max(1, targetXp)));
            var missingXp:Number = Math.max(0, targetXp - currentXp);
            var statusText:String;
            var rowHeight:Number;

            if (missingXp <= 0)
            {
                statusText = "ready for research";
                statusField = makeTooltipRowField(statusText, TOOLTIP_BODY_SIZE, TOOLTIP_TEXT_COLOR, false);
            }
            else
            {
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

        private function createTooltipTitleCostRow(marker:Object, costXp:Number):Sprite
        {
            var row:Sprite = new Sprite();
            var icon:Sprite = createTooltipMarkerIcon(
                marker != null && marker.itemType !== undefined ? String(marker.itemType) : "unknown",
                marker != null && marker.label !== undefined ? String(marker.label) : "?",
                TOOLTIP_ICON_SIZE
            );
            var titleField:TextField = makeTooltipRowField(resolveMarkerName(marker), TOOLTIP_TITLE_SIZE, TOOLTIP_TEXT_COLOR, true);
            var costField:TextField = makeTooltipHtmlRowField(
                buildTooltipHighlightedHtml("", formatExactXpValue(costXp), " XP", true),
                TOOLTIP_BODY_SIZE,
                TOOLTIP_MUTED_TEXT_COLOR,
                false
            );
            var rowHeight:Number;
            var textBlockHeight:Number;
            var textBlockTop:Number;

            if (icon != null)
            {
                row.addChild(icon);
            }

            titleField.x = TOOLTIP_ICON_LAYOUT_WIDTH + TOOLTIP_ICON_GAP;
            row.addChild(titleField);

            costField.x = titleField.x + titleField.width + TOOLTIP_PROGRESS_GAP;
            row.addChild(costField);

            rowHeight = Math.max(TOOLTIP_ICON_SIZE, Math.max(titleField.height, costField.height));
            if (icon != null)
            {
                icon.y = Math.round((rowHeight - TOOLTIP_ICON_SIZE) / 2);
            }
            textBlockHeight = Math.max(titleField.height, costField.height);
            textBlockTop = Math.round((rowHeight - textBlockHeight) / 2);
            titleField.y = textBlockTop + (textBlockHeight - titleField.height);
            costField.y = textBlockTop + (textBlockHeight - costField.height);

            return row;
        }

        private function createTooltipIconTextRow(itemType:String, fallbackLabel:String, text:String, size:int, color:uint, bold:Boolean, iconSize:Number = TOOLTIP_ICON_SIZE):Sprite
        {
            var row:Sprite = new Sprite();
            var icon:Sprite = createTooltipMarkerIcon(itemType, fallbackLabel, iconSize);
            var field:TextField = makeTooltipRowField(text, size, color, bold);
            var rowHeight:Number;

            if (icon != null)
            {
                row.addChild(icon);
            }

            field.x = TOOLTIP_ICON_LAYOUT_WIDTH + TOOLTIP_ICON_GAP;
            row.addChild(field);

            rowHeight = Math.max(iconSize, field.height);
            if (icon != null)
            {
                icon.y = Math.round((rowHeight - iconSize) / 2);
            }
            field.y = Math.round((rowHeight - field.height) / 2);
            return row;
        }

        private function createTooltipTextRow(text:String, size:int, color:uint, bold:Boolean):Sprite
        {
            var row:Sprite = new Sprite();
            var field:TextField = makeTooltipRowField(text, size, color, bold);
            row.addChild(field);
            return row;
        }

        private function createTooltipMarkerIcon(itemType:String, fallbackLabel:String, iconSize:Number = TOOLTIP_ICON_SIZE):Sprite
        {
            var iconSprite:Sprite = new Sprite();
            var bitmapData:BitmapData = getMarkerIconBitmapData(itemType);
            var iconBitmap:Bitmap;
            var scale:Number;
            var labelField:TextField;

            if (bitmapData != null)
            {
                iconBitmap = new Bitmap(bitmapData);
                iconBitmap.smoothing = true;
                scale = iconSize / Math.max(iconBitmap.width, iconBitmap.height);
                iconBitmap.scaleX = scale;
                iconBitmap.scaleY = scale;
                iconBitmap.x = Math.round((TOOLTIP_ICON_LAYOUT_WIDTH - iconBitmap.width) / 2);
                iconBitmap.y = Math.round((iconSize - iconBitmap.height) / 2);
                iconSprite.addChild(iconBitmap);
                return iconSprite;
            }

            labelField = makeTooltipRowField(fallbackLabel, TOOLTIP_BODY_SIZE, TOOLTIP_TEXT_COLOR, true);
            labelField.width = TOOLTIP_ICON_LAYOUT_WIDTH;
            labelField.height = iconSize;
            alignTextField(labelField, TextFormatAlign.CENTER);
            labelField.y = Math.round((iconSize - labelField.height) / 2);
            iconSprite.addChild(labelField);
            return iconSprite;
        }

        private function makeTooltipRowField(text:String, size:int, color:uint, bold:Boolean):TextField
        {
            var field:TextField = makeTextField(color, size, bold);
            field.text = text;
            field.width = field.textWidth + 6;
            field.height = field.textHeight + 6;
            return field;
        }

        private function makeTooltipHtmlRowField(html:String, size:int, color:uint, bold:Boolean):TextField
        {
            var field:TextField = makeTextField(color, size, bold);
            field.htmlText = html;
            field.width = field.textWidth + 6;
            field.height = field.textHeight + 6;
            return field;
        }

        private function buildTooltipHighlightedHtml(prefix:String, highlightedText:String, suffix:String, highlightBold:Boolean):String
        {
            var html:String = escapeHtml(prefix);

            html += "<font color='#" + formatHtmlColor(TOOLTIP_HIGHLIGHT_TEXT_COLOR) + "'>";
            if (highlightBold)
            {
                html += "<b>";
            }
            html += escapeHtml(highlightedText);
            if (highlightBold)
            {
                html += "</b>";
            }
            html += "</font>";
            html += escapeHtml(suffix);
            return html;
        }

        private function escapeHtml(text:String):String
        {
            if (text == null)
            {
                return "";
            }

            return text.split("&").join("&amp;").split("<").join("&lt;").split(">") .join("&gt;");
        }

        private function formatHtmlColor(color:uint):String
        {
            var hex:String = color.toString(16).toUpperCase();

            while (hex.length < 6)
            {
                hex = "0" + hex;
            }

            return hex;
        }

        private function resolveTooltipItemLabel(item:Object):String
        {
            if (item != null && item.name !== undefined && item.name != null && String(item.name).length > 0)
            {
                return String(item.name);
            }

            if (item != null && item.item_type !== undefined)
            {
                return resolveMarkerName({itemType: item.item_type});
            }

            return resolveMarkerName(null);
        }

        private function resolveMarkerName(marker:Object):String
        {
            var explicitName:String;
            var itemType:String;

            if (marker != null && marker.name !== undefined && marker.name != null)
            {
                explicitName = String(marker.name);
                if (explicitName.length > 0)
                {
                    return explicitName;
                }
            }

            itemType = marker != null && marker.itemType !== undefined ? String(marker.itemType) : "unknown";
            if (MARKER_TYPE_NAMES.hasOwnProperty(itemType))
            {
                return String(MARKER_TYPE_NAMES[itemType]);
            }

            return String(MARKER_TYPE_NAMES.unknown);
        }

        private function createMarkerIcon(itemType:String, markerTopY:Number):Bitmap
        {
            var bitmapData:BitmapData = getMarkerIconBitmapData(itemType);
            var icon:Bitmap;
            var scale:Number;

            if (bitmapData == null)
            {
                return null;
            }

            icon = new Bitmap(bitmapData);
            icon.smoothing = true;
            scale = MARKER_ICON_SIZE / Math.max(icon.width, icon.height);
            icon.scaleX = scale;
            icon.scaleY = scale;
            icon.x = -Math.round(icon.width / 2);
            icon.y = markerTopY - icon.height + MARKER_ICON_Y_OFFSET;
            return icon;
        }

        private function getMarkerIconBitmapData(itemType:String):BitmapData
        {
            var normalizedType:String = itemType != null ? itemType : "";

            if (_markerIconBitmapByType.hasOwnProperty(normalizedType))
            {
                return _markerIconBitmapByType[normalizedType] as BitmapData;
            }

            if (_markerIconLoadStateByType[normalizedType] === "failed")
            {
                return null;
            }

            if (_markerIconLoadStateByType[normalizedType] !== "loading")
            {
                beginMarkerIconLoad(normalizedType);
            }

            return null;
        }

        private function beginMarkerIconLoad(itemType:String):void
        {
            var paths:Array = getMarkerIconPaths(itemType);

            if (paths == null || paths.length == 0)
            {
                _markerIconLoadStateByType[itemType] = "failed";
                return;
            }

            _markerIconLoadStateByType[itemType] = "loading";
            loadMarkerIconCandidate(itemType, paths, 0);
        }

        private function loadMarkerIconCandidate(itemType:String, paths:Array, pathIndex:int):void
        {
            var path:String;
            var loader:Loader;
            var onComplete:Function;
            var onError:Function;

            if (paths == null || pathIndex >= paths.length)
            {
                _markerIconLoadStateByType[itemType] = "failed";
                return;
            }

            path = String(paths[pathIndex]);
            loader = new Loader();

            onComplete = function(event:Event):void
            {
                var loadedBitmap:Bitmap = loader.content as Bitmap;

                loader.contentLoaderInfo.removeEventListener(Event.COMPLETE, onComplete);
                loader.contentLoaderInfo.removeEventListener(IOErrorEvent.IO_ERROR, onError);

                if (loadedBitmap != null && loadedBitmap.bitmapData != null)
                {
                    _markerIconBitmapByType[itemType] = loadedBitmap.bitmapData.clone();
                    _markerIconLoadStateByType[itemType] = "ready";
                    try
                    {
                        loader.unload();
                    }
                    catch (error:Error)
                    {
                    }
                    if (_isReady && _context != null)
                    {
                        updateBarFromContext();
                    }
                    return;
                }

                try
                {
                    loader.unload();
                }
                catch (error2:Error)
                {
                }
                loadMarkerIconCandidate(itemType, paths, pathIndex + 1);
            };

            onError = function(event:IOErrorEvent):void
            {
                loader.contentLoaderInfo.removeEventListener(Event.COMPLETE, onComplete);
                loader.contentLoaderInfo.removeEventListener(IOErrorEvent.IO_ERROR, onError);
                try
                {
                    loader.unload();
                }
                catch (error:Error)
                {
                }
                loadMarkerIconCandidate(itemType, paths, pathIndex + 1);
            };

            loader.contentLoaderInfo.addEventListener(Event.COMPLETE, onComplete, false, 0, true);
            loader.contentLoaderInfo.addEventListener(IOErrorEvent.IO_ERROR, onError, false, 0, true);

            try
            {
                loader.load(new URLRequest(path));
            }
            catch (error:Error)
            {
                loader.contentLoaderInfo.removeEventListener(Event.COMPLETE, onComplete);
                loader.contentLoaderInfo.removeEventListener(IOErrorEvent.IO_ERROR, onError);
                loadMarkerIconCandidate(itemType, paths, pathIndex + 1);
            }
        }

        private function getMarkerIconPaths(itemType:String):Array
        {
            if (itemType == null || itemType.length == 0 || !MARKER_ICON_PATHS.hasOwnProperty(itemType))
            {
                return null;
            }

            return MARKER_ICON_PATHS[itemType] as Array;
        }

        private function drawMask(shape:Shape, posX:Number, posY:Number, width:Number, height:Number):void
        {
            shape.graphics.clear();
            if (width <= 0 || height <= 0)
            {
                return;
            }
            shape.graphics.beginFill(0xFFFFFF, 1.0);
            shape.graphics.drawRect(posX, posY, width, height);
            shape.graphics.endFill();
        }

        private function layoutFromStage():void
        {
            x = 0;
            y = 0;
            if (stage == null)
            {
                _barWidth = MIN_BAR_WIDTH;
                return;
            }
            _barWidth = Math.max(MIN_BAR_WIDTH, stage.stageWidth - SIDE_MARGIN * 2);
        }

        private function positionLabels():void
        {
            var rightEdge:Number = SIDE_MARGIN + _barWidth;
            var counterX:Number = rightEdge + COUNTER_GAP;
            var counterCaptionX:Number = counterX + COUNTER_VALUE_WIDTH + COUNTER_TEXT_GAP;

            combatPercentLabel.x = counterX;
            combatPercentLabel.y = TOP_MARGIN - combatPercentLabel.height - 1;

            combatPercentCaption.x = counterCaptionX;
            combatPercentCaption.y = combatPercentLabel.y;

            totalPercentLabel.x = counterX;
            totalPercentLabel.y = TOP_MARGIN + BAR_HEIGHT + 1;

            totalPercentCaption.x = counterCaptionX;
            totalPercentCaption.y = totalPercentLabel.y;
        }

        private function createBitmap(assetClass:Class):Bitmap
        {
            var bitmap:Bitmap = new assetClass() as Bitmap;
            bitmap.smoothing = true;
            return bitmap;
        }

        private function numberValue(value:*, fallback:Number):Number
        {
            var parsed:Number = Number(value);
            if (isNaN(parsed))
            {
                return fallback;
            }
            return parsed;
        }

        private function clamp(value:Number, minValue:Number, maxValue:Number):Number
        {
            if (value < minValue)
            {
                return minValue;
            }
            if (value > maxValue)
            {
                return maxValue;
            }
            return value;
        }

        private function makeMarkerLabelField(text:String, markerTopY:Number):TextField
        {
            var field:TextField = makeTextField(LABEL_COLOR, 10, true);
            alignTextField(field, TextFormatAlign.CENTER);
            field.width = 24;
            field.height = 14;
            field.x = -12;
            field.y = markerTopY - field.height + 1;
            field.text = text;
            return field;
        }

        private function makeCounterField():TextField
        {
            var field:TextField = makeTextField(LABEL_COLOR, 13, true);
            alignTextField(field, TextFormatAlign.RIGHT);
            field.width = COUNTER_VALUE_WIDTH;
            field.height = 16;
            return field;
        }

        private function makeCounterCaptionField(text:String):TextField
        {
            var field:TextField = makeTextField(MARKER_VALUE_COLOR, 13, false);
            alignTextField(field, TextFormatAlign.LEFT);
            field.width = COUNTER_CAPTION_WIDTH;
            field.height = 16;
            field.text = text;
            return field;
        }

        private function alignTextField(field:TextField, alignment:String):void
        {
            var format:TextFormat = field.defaultTextFormat;

            format.align = alignment;
            field.defaultTextFormat = format;
            field.setTextFormat(format);
        }

        private function formatExactXpValue(value:Number):String
        {
            var integerValue:int = Math.round(value);
            var text:String = Math.abs(integerValue).toString();
            var parts:Array = [];

            while (text.length > 3)
            {
                parts.unshift(text.substr(text.length - 3));
                text = text.substr(0, text.length - 3);
            }

            if (text.length > 0)
            {
                parts.unshift(text);
            }

            text = parts.join(" ");
            if (integerValue < 0)
            {
                text = "-" + text;
            }

            return text;
        }

        private function formatCompactValue(value:Number, suffix:String):String
        {
            var absValue:Number = Math.abs(value);
            var decimals:int;
            var precision:Number;
            var rounded:Number;
            var text:String;

            if (absValue < 10)
            {
                decimals = 2;
            }
            else if (absValue < 100)
            {
                decimals = 1;
            }
            else
            {
                decimals = 0;
            }

            precision = Math.pow(10, decimals);
            rounded = Math.round(value * precision) / precision;
            text = rounded.toFixed(decimals);

            while (text.indexOf(".") != -1 && (text.charAt(text.length - 1) == "0" || text.charAt(text.length - 1) == "."))
            {
                text = text.substr(0, text.length - 1);
            }

            return text + suffix;
        }

        private function makeTextField(color:uint, size:int, bold:Boolean):TextField
        {
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