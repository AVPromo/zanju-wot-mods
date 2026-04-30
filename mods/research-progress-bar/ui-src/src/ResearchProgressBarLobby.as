package
{
    import flash.display.Bitmap;
    import flash.display.Shape;
    import flash.display.Sprite;
    import flash.events.Event;
    import flash.text.TextField;
    import flash.text.TextFormat;
    import flash.text.TextFormatAlign;
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
        private static const TOP_MARGIN:Number = 100;
        private static const MIN_BAR_WIDTH:Number = 80;
        private static const BAR_HEIGHT:Number = 8;
        private static const LABEL_COLOR:uint = 0xF4F0E8;
        private static const COUNTER_GAP:Number = 14;
        private static const COUNTER_VALUE_WIDTH:Number = 36;
        private static const COUNTER_TEXT_GAP:Number = 4;
        private static const COUNTER_CAPTION_WIDTH:Number = 68;
        private static const MARKER_VALUE_COLOR:uint = 0xAAA69A;
        private static const MARKER_VALUE_WIDTH:Number = 44;
        private static const MARKER_VALUE_ROW_STEP:Number = 13;
        private static const MARKER_VALUE_MIN_GAP:Number = 4;

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
        private var _context:Object;
        private var _barWidth:Number = MIN_BAR_WIDTH;
        private var _isReady:Boolean = false;

        public function ResearchProgressBarLobby()
        {
            super();
        }

        override protected function configUI():void
        {
            super.configUI();
            mouseEnabled = false;
            mouseChildren = false;
            build();

            if (stage != null)
            {
                stage.addEventListener(Event.RESIZE, onStageResize);
            }
        }

        override protected function onDispose():void
        {
            if (stage != null)
            {
                stage.removeEventListener(Event.RESIZE, onStageResize);
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
            addChild(markersContainer);
        }

        private function onStageResize(event:Event):void
        {
            layoutFromStage();
            updateBarFromContext();
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
            var markerValueRowRightEdges:Array = [-1000000, -1000000, -1000000];

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
                layoutMarkerValueLabel(markerDisplay, markerValueRowRightEdges);
                markersContainer.addChild(markerDisplay);
            }
        }

        private function createMarkerDisplay(marker:Object, markerCostXp:Number, combatXp:Number, freeXp:Number):Sprite
        {
            var markerSprite:Sprite = new Sprite();
            var markerBitmap:Bitmap = createMarkerBitmap(markerCostXp, combatXp, freeXp);
            var markerLabel:TextField;
            var markerValueLabel:TextField;
            var markerLabelText:String = marker != null && marker.label !== undefined ? String(marker.label) : "";

            markerBitmap.x = -Math.round(markerBitmap.width / 2);
            markerBitmap.y = -Math.round((markerBitmap.height - BAR_HEIGHT) / 2);
            markerSprite.addChild(markerBitmap);

            if (markerLabelText.length > 0)
            {
                markerLabel = makeMarkerLabelField(markerLabelText, markerBitmap.y);
                markerSprite.addChild(markerLabel);
            }

            markerValueLabel = makeMarkerValueField(formatXpValue(markerCostXp), markerBitmap.y + markerBitmap.height + 3);
            markerValueLabel.name = "markerValueLabel";
            markerSprite.addChild(markerValueLabel);

            return markerSprite;
        }

        private function layoutMarkerValueLabel(markerDisplay:Sprite, rowRightEdges:Array):void
        {
            var markerValueLabel:TextField = markerDisplay.getChildByName("markerValueLabel") as TextField;
            var labelLeft:Number;
            var labelRight:Number;
            var rowIndex:int;

            if (markerValueLabel == null)
            {
                return;
            }

            labelLeft = markerDisplay.x + markerValueLabel.x;
            labelRight = labelLeft + markerValueLabel.width;
            rowIndex = chooseMarkerValueRow(labelLeft, rowRightEdges);
            markerValueLabel.y += rowIndex * MARKER_VALUE_ROW_STEP;
            rowRightEdges[rowIndex] = labelRight;
        }

        private function chooseMarkerValueRow(labelLeft:Number, rowRightEdges:Array):int
        {
            var rowIndex:int;
            var bestIndex:int = 0;
            var bestRight:Number = Number.MAX_VALUE;
            var rowRight:Number;

            for (rowIndex = 0; rowIndex < rowRightEdges.length; rowIndex++)
            {
                rowRight = Number(rowRightEdges[rowIndex]);
                if (labelLeft >= rowRight + MARKER_VALUE_MIN_GAP)
                {
                    return rowIndex;
                }
                if (rowRight < bestRight)
                {
                    bestRight = rowRight;
                    bestIndex = rowIndex;
                }
            }

            return bestIndex;
        }

        private function createMarkerBitmap(markerCostXp:Number, combatXp:Number, freeXp:Number):Bitmap
        {
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

        private function makeMarkerValueField(text:String, labelY:Number):TextField
        {
            var field:TextField = makeTextField(MARKER_VALUE_COLOR, 9, false);
            alignTextField(field, TextFormatAlign.CENTER);
            field.width = MARKER_VALUE_WIDTH;
            field.height = 12;
            field.x = -Math.round(MARKER_VALUE_WIDTH / 2);
            field.y = labelY;
            field.text = text;
            return field;
        }

        private function makeCounterField():TextField
        {
            var field:TextField = makeTextField(LABEL_COLOR, 11, true);
            alignTextField(field, TextFormatAlign.RIGHT);
            field.width = COUNTER_VALUE_WIDTH;
            field.height = 14;
            return field;
        }

        private function makeCounterCaptionField(text:String):TextField
        {
            var field:TextField = makeTextField(LABEL_COLOR, 11, false);
            alignTextField(field, TextFormatAlign.LEFT);
            field.width = COUNTER_CAPTION_WIDTH;
            field.height = 14;
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

        private function formatXpValue(value:Number):String
        {
            var absValue:Number = Math.abs(value);

            if (absValue < 1000)
            {
                return int(value).toString();
            }
            if (absValue < 999500)
            {
                return formatCompactValue(value / 1000, "k");
            }
            return formatCompactValue(value / 1000000, "M");
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