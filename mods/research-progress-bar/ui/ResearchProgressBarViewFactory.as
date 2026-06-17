package {
    import flash.display.Bitmap;
    import flash.display.Shape;
    import flash.display.Sprite;
    import flash.text.TextField;
    import flash.text.TextFieldAutoSize;
    import flash.text.TextFormat;
    import flash.text.TextFormatAlign;

    public final class ResearchProgressBarViewFactory {
        private static const COUNTER_VERTICAL_PADDING:Number = 8;
        private static const SEPARATE_STATUS_COLOR:uint = 0x80D43A;
        private static const SEPARATE_STATUS_FONT_SIZE:int = 15;

        public static function build(
            host:Sprite,
            progressBarBaseAsset:Class,
            progressBarWhiteAsset:Class,
            progressBarGreenAsset:Class,
            progressBarYellowAsset:Class,
            labelColor:uint,
            markerValueColor:uint,
            counterFontSize:int,
            counterFieldHeight:Number
        ):Object {
            var parts:Object = {};

            parts.combatPercentLabel = makeCounterField(labelColor, counterFontSize, counterFieldHeight);
            host.addChild(parts.combatPercentLabel);

            parts.combatPercentCaption = makeCounterCaptionField(
                "Vehicle XP",
                markerValueColor,
                counterFontSize,
                counterFieldHeight
            );
            host.addChild(parts.combatPercentCaption);

            parts.totalPercentLabel = makeCounterField(labelColor, counterFontSize, counterFieldHeight);
            host.addChild(parts.totalPercentLabel);

            parts.totalPercentCaption = makeCounterCaptionField(
                "Total XP",
                markerValueColor,
                counterFontSize,
                counterFieldHeight
            );
            host.addChild(parts.totalPercentCaption);

            parts.sideCounterLabel = makeCounterField(labelColor, counterFontSize, counterFieldHeight);
            alignTextField(parts.sideCounterLabel, TextFormatAlign.LEFT);
            host.addChild(parts.sideCounterLabel);

            parts.sideCounterCaption = makeCounterCaptionField(
                "",
                markerValueColor,
                counterFontSize,
                counterFieldHeight
            );
            alignTextField(parts.sideCounterCaption, TextFormatAlign.LEFT);
            host.addChild(parts.sideCounterCaption);

            parts.baseBar = createBitmap(progressBarBaseAsset);
            host.addChild(parts.baseBar);

            parts.completedBar = createBitmap(progressBarWhiteAsset);
            host.addChild(parts.completedBar);

            parts.combatBar = createBitmap(progressBarGreenAsset);
            host.addChild(parts.combatBar);

            parts.freeBar = createBitmap(progressBarYellowAsset);
            host.addChild(parts.freeBar);

            parts.completedMaskShape = new Shape();
            parts.completedMaskShape.visible = false;
            host.addChild(parts.completedMaskShape);

            parts.combatMaskShape = new Shape();
            parts.combatMaskShape.visible = false;
            host.addChild(parts.combatMaskShape);

            parts.freeMaskShape = new Shape();
            parts.freeMaskShape.visible = false;
            host.addChild(parts.freeMaskShape);

            parts.completedBar.mask = parts.completedMaskShape;
            parts.combatBar.mask = parts.combatMaskShape;
            parts.freeBar.mask = parts.freeMaskShape;

            parts.markersContainer = new Sprite();
            parts.markersContainer.mouseEnabled = false;
            host.addChild(parts.markersContainer);

            parts.modeButtonsContainer = new Sprite();
            parts.modeButtonsContainer.mouseEnabled = false;
            parts.modeButtonsContainer.mouseChildren = true;
            parts.modeButtonsContainer.visible = false;
            host.addChild(parts.modeButtonsContainer);

            parts.separateStatusLabel = makeSeparateStatusField();
            parts.separateStatusLabel.visible = false;
            host.addChild(parts.separateStatusLabel);

            parts.tooltipContainer = new Sprite();
            parts.tooltipContainer.mouseEnabled = false;
            parts.tooltipContainer.mouseChildren = false;
            parts.tooltipContainer.visible = false;

            parts.tooltipBackground = new Shape();
            parts.tooltipContainer.addChild(parts.tooltipBackground);

            parts.tooltipContent = new Sprite();
            parts.tooltipContent.mouseEnabled = false;
            parts.tooltipContent.mouseChildren = false;
            parts.tooltipContainer.addChild(parts.tooltipContent);

            host.addChild(parts.tooltipContainer);

            return parts;
        }

        private static function createBitmap(assetClass:Class):Bitmap {
            var bitmap:Bitmap = new assetClass() as Bitmap;
            bitmap.smoothing = true;
            return bitmap;
        }

        private static function makeCounterField(color:uint, size:int, fieldHeight:Number):TextField {
            var field:TextField = makeTextField(color, size, true);
            alignTextField(field, TextFormatAlign.RIGHT);
            field.width = ResearchProgressBarCounterLayout.COUNTER_VALUE_WIDTH;
            field.height = resolveCounterFieldHeight(size, fieldHeight);
            return field;
        }

        private static function makeCounterCaptionField(
            text:String,
            color:uint,
            size:int,
            fieldHeight:Number
        ):TextField {
            var field:TextField = makeTextField(color, size, false);
            alignTextField(field, TextFormatAlign.LEFT);
            field.width = ResearchProgressBarCounterLayout.COUNTER_CAPTION_WIDTH;
            field.height = resolveCounterFieldHeight(size, fieldHeight);
            ResearchProgressBarFonts.setText(field, text);
            return field;
        }

        private static function makeSeparateStatusField():TextField {
            var field:TextField = makeTextField(SEPARATE_STATUS_COLOR, SEPARATE_STATUS_FONT_SIZE, true);

            alignTextField(field, TextFormatAlign.LEFT);
            field.autoSize = TextFieldAutoSize.LEFT;
            return field;
        }

        private static function resolveCounterFieldHeight(size:int, fieldHeight:Number):Number {
            return Math.max(fieldHeight, size + COUNTER_VERTICAL_PADDING);
        }

        private static function alignTextField(field:TextField, alignment:String):void {
            var format:TextFormat = field.defaultTextFormat;

            format.align = alignment;
            field.defaultTextFormat = format;
            field.setTextFormat(format);
        }

        private static function makeTextField(color:uint, size:int, bold:Boolean):TextField {
            var field:TextField = ResearchProgressBarFonts.configureTextField(new TextField());
            field.defaultTextFormat = new TextFormat(ResearchProgressBarFonts.FONT_NAME, size, color, bold);
            field.selectable = false;
            field.mouseEnabled = false;
            field.textColor = color;
            field.multiline = false;
            field.wordWrap = false;
            return field;
        }
    }
}