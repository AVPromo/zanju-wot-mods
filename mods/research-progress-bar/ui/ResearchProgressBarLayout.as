package {
    public final class ResearchProgressBarLayout {
        public static const DEFAULT_BAR_X:Number = 600;
        public static const DEFAULT_BAR_Y:Number = 105;
        public static const BAR_MIN_STAGE_SIDE_MARGIN:Number = 24;
        public static const MIN_BAR_WIDTH:Number = 80;
        public static const BAR_HEIGHT:Number = 8;
        public static const BAR_ASSEMBLY_ABOVE_HEIGHT:Number = 25;
        public static const BAR_ASSEMBLY_BELOW_HEIGHT:Number = 3;
        public static const BAR_ASSEMBLY_HEIGHT:Number = 36;

        private static const BAR_SIDE_SAFE_OFFSET:Number = 20;
        private static const LAYOUT_DISTANCE_BUCKETS:Array = [
            { minWidth: 2560, buttonBottom: 74, verticalDistance: 81, horizontalDistance: 367 },
            { minWidth: 1920, buttonBottom: 70, verticalDistance: 50, horizontalDistance: 367 },
            { minWidth: 1600, buttonBottom: 53, verticalDistance: 46, horizontalDistance: 271 },
            { minWidth: 0, buttonBottom: 51, verticalDistance: 38, horizontalDistance: 271 }
        ];

        public static function defaultLayout():Object {
            return {
                barX: DEFAULT_BAR_X,
                barY: DEFAULT_BAR_Y,
                barWidth: MIN_BAR_WIDTH
            };
        }

        public static function calculate(stageWidth:Number, stageHeight:Number):Object {
            var sideInset:Number = resolveRightRailCutoff(stageWidth) + BAR_SIDE_SAFE_OFFSET;
            var leftEdge:Number = sideInset;
            var rightEdge:Number = Math.round(stageWidth - sideInset);
            var barX:Number;
            var maxWidth:Number;

            if (rightEdge <= leftEdge + MIN_BAR_WIDTH) {
                leftEdge = BAR_MIN_STAGE_SIDE_MARGIN;
                rightEdge = stageWidth - BAR_MIN_STAGE_SIDE_MARGIN;
            }

            barX = Math.max(0, Math.round(leftEdge));
            maxWidth = Math.max(MIN_BAR_WIDTH, stageWidth - barX - BAR_MIN_STAGE_SIDE_MARGIN);

            return {
                barX: barX,
                barY: resolveBarTopFromStage(stageWidth, stageHeight),
                barWidth: clamp(Math.round(rightEdge - barX), MIN_BAR_WIDTH, maxWidth)
            };
        }

        private static function resolveLayoutDistanceBucket(stageWidth:Number):Object {
            var bucket:Object;

            for each (bucket in LAYOUT_DISTANCE_BUCKETS) {
                if (stageWidth >= Number(bucket.minWidth)) {
                    return bucket;
                }
            }

            return LAYOUT_DISTANCE_BUCKETS[LAYOUT_DISTANCE_BUCKETS.length - 1];
        }

        private static function resolveRightRailCutoff(stageWidth:Number):Number {
            return Number(resolveLayoutDistanceBucket(stageWidth).horizontalDistance);
        }

        private static function resolveVerticalBoundaryOffset(stageWidth:Number):Number {
            return Number(resolveLayoutDistanceBucket(stageWidth).verticalDistance);
        }

        private static function resolveBarTopFromStage(stageWidth:Number, stageHeight:Number):Number {
            var centeredAssemblyTop:Number;
            var centeredBarTop:Number;
            var maxBarTop:Number = Math.max(0, stageHeight - BAR_HEIGHT - BAR_ASSEMBLY_BELOW_HEIGHT);
            var buttonBottom:Number = Number(resolveLayoutDistanceBucket(stageWidth).buttonBottom);

            centeredAssemblyTop = buttonBottom + Math.round((resolveVerticalBoundaryOffset(stageWidth) - BAR_ASSEMBLY_HEIGHT) * 0.5);
            centeredBarTop = centeredAssemblyTop + BAR_ASSEMBLY_ABOVE_HEIGHT;
            return clamp(centeredBarTop, BAR_ASSEMBLY_ABOVE_HEIGHT, maxBarTop);
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