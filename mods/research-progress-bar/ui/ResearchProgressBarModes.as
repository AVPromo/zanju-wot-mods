package {
    import flash.display.Shape;
    import flash.display.Sprite;
    import flash.events.MouseEvent;
    import flash.text.TextField;
    import flash.text.TextFormat;
    import flash.text.TextFormatAlign;
    import flash.utils.Dictionary;

    public final class ResearchProgressBarModes {
        private static const MODE_BUTTON_GAP:Number = 6;
        private static const MODE_BUTTON_BAR_GAP:Number = 15;
        private static const MODE_BUTTON_HEIGHT:Number = 20;
        private static const MODE_BUTTON_BOTTOM_PADDING:Number = 1;
        private static const MODE_BUTTON_PADDING_X:Number = 10;
        private static const MODE_BUTTON_TEXT_COLOR:uint = 0xD4CAB8;
        private static const MODE_BUTTON_TEXT_ACTIVE_COLOR:uint = 0xF0CF74;
        private static const MODE_BUTTON_BACKGROUND_COLOR:uint = 0x141414;
        private static const MODE_BUTTON_BACKGROUND_ACTIVE_COLOR:uint = 0x4A3A1F;
        private static const MODE_BUTTON_BORDER_COLOR:uint = 0x6C5B47;
        private static const MODE_BUTTON_BORDER_ACTIVE_COLOR:uint = 0xA48745;

        public static function resolveModes(context:Object):Array {
            if (context == null) {
                return [];
            }

            if (context.modes is Array) {
                return context.modes as Array;
            }

            return [ {
                    id: "legacy_research",
                    buttonLabel: "Research",
                    barMaxValue: context.maxRequirementXp,
                    completedValue: context.completedValue,
                    primaryValue: context.combatXp,
                    secondaryValue: context.freeXp,
                    leftCounterText: context.leftCounterText,
                    leftCounterCaption: context.leftCounterCaption,
                    rightCounterText: context.rightCounterText,
                    rightCounterCaption: context.rightCounterCaption,
                    sideCounterText: context.sideCounterText,
                    sideCounterCaption: context.sideCounterCaption,
                    markers: context.markers
                }
            ];
        }

        public static function syncSelectedMode(context:Object, modes:Array, selectedModeId:String):String {
            var requestedModeId:String = context != null && context.selectedModeId !== undefined
                ? String(context.selectedModeId)
                : null;

            if (!hasModeId(modes, selectedModeId)) {
                selectedModeId = null;
            }

            if (selectedModeId == null && hasModeId(modes, requestedModeId)) {
                selectedModeId = requestedModeId;
            }

            if (selectedModeId == null && modes != null && modes.length > 0) {
                selectedModeId = modeIdOf(modes[0]);
            }

            return selectedModeId;
        }

        public static function resolveSelectedMode(modes:Array, selectedModeId:String):Object {
            var mode:Object;

            if (modes == null) {
                return null;
            }

            for each (mode in modes) {
                if (modeIdOf(mode) == selectedModeId) {
                    return mode;
                }
            }

            return null;
        }

        public static function modeIdOf(mode:Object):String {
            if (mode == null || mode.id === undefined || mode.id == null) {
                return null;
            }

            return String(mode.id);
        }

        public static function rebuildModeButtons(
            container:Sprite,
            modes:Array,
            selectedModeId:String,
            barX:Number,
            barY:Number,
            barHeight:Number,
            minStageSideMargin:Number,
            clickHandler:Function
        ):Dictionary {
            var layout:Object = resolveModeButtonsLayout(
                modes,
                barX,
                barY,
                barHeight,
                minStageSideMargin
            );
            var cursorX:Number = Number(layout.x);
            var buttonY:Number = Number(layout.y);
            var mode:Object;
            var button:Sprite;
            var modeIdByButton:Dictionary = clearModeButtons(container, clickHandler);

            if (container == null || modes == null || modes.length == 0) {
                return modeIdByButton;
            }

            container.visible = true;

            for each (mode in modes) {
                button = createModeButton(resolveModeButtonLabel(mode), modeIdOf(mode) == selectedModeId);
                button.x = cursorX;
                button.y = buttonY;
                button.buttonMode = true;
                button.useHandCursor = true;
                button.mouseEnabled = true;
                button.addEventListener(MouseEvent.CLICK, clickHandler, false, 0, true);
                modeIdByButton[button] = modeIdOf(mode);
                container.addChild(button);
                cursorX += button.width + MODE_BUTTON_GAP;
            }

            return modeIdByButton;
        }

        public static function resolveModeButtonsLayout(
            modes:Array,
            barX:Number,
            barY:Number,
            barHeight:Number,
            minStageSideMargin:Number
        ):Object {
            var totalWidth:Number = measureModeButtonsWidth(modes);
            var buttonHeight:Number = MODE_BUTTON_HEIGHT + MODE_BUTTON_BOTTOM_PADDING;

            return {
                x: Math.max(minStageSideMargin, barX - MODE_BUTTON_BAR_GAP - totalWidth),
                y: barY + Math.round((barHeight - buttonHeight) * 0.5),
                width: totalWidth,
                height: buttonHeight
            };
        }

        public static function clearModeButtons(container:Sprite, clickHandler:Function):Dictionary {
            var child:Sprite;
            var modeIdByButton:Dictionary = new Dictionary(true);

            if (container == null) {
                return modeIdByButton;
            }

            while (container.numChildren > 0) {
                child = container.removeChildAt(0) as Sprite;
                if (child != null) {
                    child.removeEventListener(MouseEvent.CLICK, clickHandler);
                }
            }

            container.visible = false;
            return modeIdByButton;
        }

        private static function hasModeId(modes:Array, modeId:String):Boolean {
            var mode:Object;

            if (modeId == null || modes == null) {
                return false;
            }

            for each (mode in modes) {
                if (modeIdOf(mode) == modeId) {
                    return true;
                }
            }

            return false;
        }

        private static function resolveModeButtonLabel(mode:Object):String {
            if (mode != null && mode.buttonLabel !== undefined && mode.buttonLabel != null) {
                return String(mode.buttonLabel);
            }

            return "Mode";
        }

        private static function measureModeButtonsWidth(modes:Array):Number {
            var totalWidth:Number = 0;
            var mode:Object;

            if (modes == null || modes.length == 0) {
                return 0;
            }

            for each (mode in modes) {
                totalWidth += measureModeButtonWidth(resolveModeButtonLabel(mode));
            }

            if (modes.length > 1) {
                totalWidth += MODE_BUTTON_GAP * (modes.length - 1);
            }

            return totalWidth;
        }

        private static function measureModeButtonWidth(label:String):Number {
            var field:TextField = makeTextField(MODE_BUTTON_TEXT_COLOR, 12, true);

            field.text = label;
            return Math.ceil(field.textWidth + MODE_BUTTON_PADDING_X * 2 + 6);
        }

        private static function createModeButton(label:String, isSelected:Boolean):Sprite {
            var button:Sprite = new Sprite();
            var background:Shape = new Shape();
            var field:TextField = makeTextField(
                isSelected ? MODE_BUTTON_TEXT_ACTIVE_COLOR : MODE_BUTTON_TEXT_COLOR,
                12,
                true
            );
            var buttonWidth:Number;

            field.text = label;
            buttonWidth = Math.ceil(field.textWidth + MODE_BUTTON_PADDING_X * 2 + 6);
            drawModeButtonBackground(background, buttonWidth, MODE_BUTTON_HEIGHT + MODE_BUTTON_BOTTOM_PADDING, isSelected);
            button.addChild(background);

            field.width = buttonWidth;
            field.height = MODE_BUTTON_HEIGHT + 4;
            alignTextField(field, TextFormatAlign.CENTER);
            field.y = resolveCenteredTextY(field, 0, MODE_BUTTON_HEIGHT) + 1;
            button.addChild(field);

            return button;
        }

        private static function drawModeButtonBackground(shape:Shape, width:Number, height:Number, isSelected:Boolean):void {
            shape.graphics.clear();
            shape.graphics.lineStyle(
                1,
                isSelected ? MODE_BUTTON_BORDER_ACTIVE_COLOR : MODE_BUTTON_BORDER_COLOR,
                1.0
            );
            shape.graphics.beginFill(
                isSelected ? MODE_BUTTON_BACKGROUND_ACTIVE_COLOR : MODE_BUTTON_BACKGROUND_COLOR,
                0.95
            );
            shape.graphics.drawRoundRect(0, 0, width, height, 6, 6);
            shape.graphics.endFill();
        }

        private static function resolveCenteredTextY(field:TextField, containerTop:Number, containerHeight:Number):Number {
            return containerTop + Math.round((containerHeight - field.textHeight) / 2) - 2;
        }

        private static function alignTextField(field:TextField, alignment:String):void {
            var format:TextFormat = field.defaultTextFormat;

            if (format == null) {
                format = new TextFormat();
            }
            format.align = alignment;
            field.defaultTextFormat = format;
            field.setTextFormat(format);
        }

        private static function makeTextField(color:uint, size:int, bold:Boolean):TextField {
            var field:TextField = ResearchProgressBarFonts.configureTextField(new TextField());
            field.defaultTextFormat = new TextFormat(ResearchProgressBarFonts.FONT_NAME, size, color, bold);
            field.textColor = color;
            field.selectable = false;
            field.mouseEnabled = false;
            field.multiline = false;
            field.wordWrap = false;
            return field;
        }
    }
}