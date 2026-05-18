package {
    public final class ResearchProgressBarFill {
        public static function resolve(
            activeMode:Object,
            context:Object,
            barWidth:Number,
            completedOnly:Boolean
        ):Object {
            var barMaxValue:Number = Math.max(1, numberValue(activeMode.barMaxValue, numberValue(context.maxRequirementXp, 1)));
            var completedValue:Number = clamp(numberValue(activeMode.completedValue, 0), 0, barMaxValue);
            var primaryValue:Number = clamp(
                numberValue(activeMode.primaryValue, numberValue(context.combatXp, 0)),
                0,
                barMaxValue - completedValue
            );
            var secondaryValue:Number = clamp(
                numberValue(activeMode.secondaryValue, numberValue(context.freeXp, 0)),
                0,
                barMaxValue - completedValue - primaryValue
            );
            var totalProgressValue:Number = clamp(completedValue + primaryValue + secondaryValue, 0, barMaxValue);
            var completedWidth:Number = Math.round(barWidth * completedValue / barMaxValue);
            var primaryWidth:Number = Math.round(barWidth * primaryValue / barMaxValue);
            var secondaryWidth:Number = Math.round(barWidth * secondaryValue / barMaxValue);
            var markerPrimaryValue:Number = primaryValue;
            var markerSecondaryValue:Number = secondaryValue;

            if (completedOnly) {
                completedWidth = Math.round(barWidth * totalProgressValue / barMaxValue);
                primaryWidth = 0;
                secondaryWidth = 0;
                markerPrimaryValue = totalProgressValue;
                markerSecondaryValue = 0;
            }

            return {
                barMaxValue: barMaxValue,
                completedValue: completedValue,
                primaryValue: primaryValue,
                secondaryValue: secondaryValue,
                totalProgressValue: totalProgressValue,
                completedWidth: completedWidth,
                primaryWidth: primaryWidth,
                secondaryWidth: secondaryWidth,
                defaultPrimaryPercent: int(Math.min(100, primaryValue * 100 / barMaxValue)),
                defaultTotalPercent: int(Math.min(100, (primaryValue + secondaryValue) * 100 / barMaxValue)),
                markerPrimaryValue: markerPrimaryValue,
                markerSecondaryValue: markerSecondaryValue
            };
        }

        private static function numberValue(value:*, fallback:Number):Number {
            var parsed:Number = Number(value);
            if (isNaN(parsed)) {
                return fallback;
            }

            return parsed;
        }

        private static function clamp(value:Number, minValue:Number, maxValue:Number):Number {
            if (value < minValue) {
                return minValue;
            }
            if (value > maxValue) {
                return maxValue;
            }

            return value;
        }
    }
}