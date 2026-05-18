package {
    import flash.text.TextField;

    public final class ResearchProgressBarCounterLayout {
        public static const LEFT_COUNTER_OFFSET:Number = 3;
        public static const COUNTER_VALUE_WIDTH:Number = 60;
        public static const COUNTER_TEXT_GAP:Number = 5;
        public static const COUNTER_CAPTION_WIDTH:Number = 110;
        public static const COUNTER_TOP_OFFSET:Number = 5;
        public static const RIGHT_COUNTER_VALUE_OFFSET:Number = 3;
        public static const COUNTER_LAYOUT_RIGHT_SINGLE:String = "right_single";
        public static const COUNTER_LAYOUT_ELITE_STATUS:String = "elite_status";
        public static const ELITE_STATUS_WIDTH:Number = 210;

        public static function positionLabels(
            activeCounterLayout:String,
            barX:Number,
            barY:Number,
            barWidth:Number,
            barHeight:Number,
            combatPercentLabel:TextField,
            combatPercentCaption:TextField,
            totalPercentLabel:TextField,
            totalPercentCaption:TextField,
            sideCounterLabel:TextField,
            sideCounterCaption:TextField
        ):void {
            var counterTop:Number = barY + barHeight + 1 + COUNTER_TOP_OFFSET;
            var leftCounterX:Number = barX - LEFT_COUNTER_OFFSET;
            var rightCounterEdge:Number = barX + barWidth;

            if (activeCounterLayout == COUNTER_LAYOUT_RIGHT_SINGLE) {
                positionRightCounterGroup(totalPercentLabel, totalPercentCaption, rightCounterEdge, counterTop);
                return;
            }

            if (activeCounterLayout == COUNTER_LAYOUT_ELITE_STATUS) {
                combatPercentLabel.x = leftCounterX;
                combatPercentLabel.y = counterTop;

                combatPercentCaption.x = leftCounterX;
                combatPercentCaption.y = counterTop + combatPercentLabel.height;

                positionRightCounterGroup(totalPercentLabel, totalPercentCaption, rightCounterEdge, counterTop);
                return;
            }

            if (hasCounterText(sideCounterLabel) || hasCounterText(sideCounterCaption)) {
                positionLeftCounterGroup(sideCounterLabel, sideCounterCaption, leftCounterX, counterTop);
            }

            positionRightCounterGroup(combatPercentLabel, combatPercentCaption, rightCounterEdge, counterTop);
            positionRightCounterGroup(totalPercentLabel, totalPercentCaption, rightCounterEdge, counterTop + combatPercentLabel.height);
        }

        private static function positionLeftCounterGroup(valueField:TextField, captionField:TextField, groupX:Number, groupY:Number):void {
            var valueWidth:Number = resolveDisplayTextWidth(valueField);
            var captionWidth:Number = hasCounterText(captionField) ? resolveDisplayTextWidth(captionField) : 0;

            valueField.width = valueWidth;
            valueField.x = groupX;
            valueField.y = groupY;

            if (captionField != null) {
                captionField.width = captionWidth;
                captionField.x = groupX + valueWidth + (captionWidth > 0 ? COUNTER_TEXT_GAP : 0);
                captionField.y = groupY;
            }
        }

        private static function positionRightCounterGroup(valueField:TextField, captionField:TextField, rightEdge:Number, groupY:Number):void {
            var captionWidth:Number = hasCounterText(captionField) ? COUNTER_CAPTION_WIDTH : 0;

            valueField.width = COUNTER_VALUE_WIDTH;
            valueField.x = rightEdge - COUNTER_VALUE_WIDTH + RIGHT_COUNTER_VALUE_OFFSET;
            valueField.y = groupY;

            if (captionField != null) {
                captionField.width = captionWidth;
                captionField.x = valueField.x - (captionWidth > 0 ? COUNTER_TEXT_GAP + COUNTER_CAPTION_WIDTH : 0);
                captionField.y = groupY;
            }
        }

        private static function resolveDisplayTextWidth(field:TextField):Number {
            if (field == null || field.text == null || field.text.length == 0) {
                return 0;
            }

            return Math.max(1, Math.ceil(field.textWidth + 4));
        }

        private static function hasCounterText(field:TextField):Boolean {
            return field != null && field.text != null && field.text.length > 0;
        }
    }
}