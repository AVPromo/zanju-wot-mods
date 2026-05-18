package {
    import flash.text.TextField;
    import flash.text.TextFormat;
    import flash.text.TextFormatAlign;

    public final class ResearchProgressBarCounterFields {
        public static function resolveState(activeMode:Object):Object {
            return {
                counterLayout: activeMode != null && activeMode.counterLayout !== undefined
                    ? String(activeMode.counterLayout)
                    : "",
                barFillMode: activeMode != null && activeMode.barFillMode !== undefined
                    ? String(activeMode.barFillMode)
                    : ""
            };
        }

        public static function apply(
            activeMode:Object,
            defaultPrimaryPercent:int,
            defaultTotalPercent:int,
            combatPercentLabel:TextField,
            combatPercentCaption:TextField,
            totalPercentLabel:TextField,
            totalPercentCaption:TextField,
            sideCounterLabel:TextField,
            sideCounterCaption:TextField
        ):Object {
            var state:Object = resolveState(activeMode);
            var activeCounterLayout:String = String(state.counterLayout);
            var activeBarFillMode:String = String(state.barFillMode);
            var leftCounterText:String = resolveModeText(
                activeMode,
                "leftCounterText",
                defaultPrimaryPercent.toString() + "%"
            );
            var leftCounterCaption:String = resolveModeText(activeMode, "leftCounterCaption", "Vehicle XP");
            var rightCounterText:String = resolveModeText(
                activeMode,
                "rightCounterText",
                defaultTotalPercent.toString() + "%"
            );
            var rightCounterCaption:String = resolveModeText(activeMode, "rightCounterCaption", "Total XP");
            var sideCounterText:String = resolveModeText(activeMode, "sideCounterText", "");
            var sideCounterCaptionText:String = resolveModeText(activeMode, "sideCounterCaption", "");

            combatPercentLabel.text = leftCounterText;
            totalPercentLabel.text = rightCounterText;
            totalPercentCaption.text = rightCounterCaption;
            sideCounterLabel.text = sideCounterText;
            sideCounterCaption.text = sideCounterCaptionText;

            alignTextField(totalPercentLabel, TextFormatAlign.RIGHT);
            alignTextField(totalPercentCaption, TextFormatAlign.RIGHT);
            alignTextField(sideCounterLabel, TextFormatAlign.LEFT);
            alignTextField(sideCounterCaption, TextFormatAlign.LEFT);
            totalPercentLabel.width = ResearchProgressBarCounterLayout.COUNTER_VALUE_WIDTH;
            totalPercentCaption.width = ResearchProgressBarCounterLayout.COUNTER_CAPTION_WIDTH;
            sideCounterLabel.width = ResearchProgressBarCounterLayout.COUNTER_VALUE_WIDTH;
            sideCounterCaption.width = ResearchProgressBarCounterLayout.COUNTER_CAPTION_WIDTH;

            if (activeCounterLayout == ResearchProgressBarCounterLayout.COUNTER_LAYOUT_ELITE_STATUS) {
                alignTextField(combatPercentLabel, TextFormatAlign.LEFT);
                alignTextField(combatPercentCaption, TextFormatAlign.LEFT);
                combatPercentLabel.width = ResearchProgressBarCounterLayout.ELITE_STATUS_WIDTH;
                combatPercentCaption.width = ResearchProgressBarCounterLayout.ELITE_STATUS_WIDTH;
                combatPercentCaption.htmlText = ResearchProgressBarTooltipContent.buildEliteStatusCounterHtml(leftCounterCaption);
            }
            else {
                combatPercentCaption.text = leftCounterCaption;
                alignTextField(combatPercentLabel, TextFormatAlign.RIGHT);
                alignTextField(combatPercentCaption, TextFormatAlign.RIGHT);
                combatPercentLabel.width = ResearchProgressBarCounterLayout.COUNTER_VALUE_WIDTH;
                combatPercentCaption.width = ResearchProgressBarCounterLayout.COUNTER_CAPTION_WIDTH;
            }

            return state;
        }

        private static function resolveModeText(activeMode:Object, key:String, fallback:String):String {
            if (activeMode != null && activeMode[key] !== undefined) {
                return String(activeMode[key]);
            }

            return fallback;
        }

        private static function alignTextField(field:TextField, alignment:String):void {
            var format:TextFormat = field.defaultTextFormat;

            format.align = alignment;
            field.defaultTextFormat = format;
            field.setTextFormat(format);
        }
    }
}