package {
    import flash.display.Stage;
    import flash.display.StageAlign;
    import flash.display.StageScaleMode;
    import flash.events.Event;
    import flash.events.MouseEvent;

    public final class ResearchProgressBarStageSupport {
        public static function attachListeners(
            stageSpace:Stage,
            onStageResize:Function,
            onStageMouseMove:Function,
            onStageMouseLeave:Function
        ):void {
            if (stageSpace == null) {
                return;
            }

            stageSpace.align = StageAlign.TOP_LEFT;
            stageSpace.scaleMode = StageScaleMode.NO_SCALE;

            detachListeners(stageSpace, onStageResize, onStageMouseMove, onStageMouseLeave);
            stageSpace.addEventListener(Event.RESIZE, onStageResize);
            stageSpace.addEventListener(MouseEvent.MOUSE_MOVE, onStageMouseMove, false, 0, true);
            stageSpace.addEventListener(Event.MOUSE_LEAVE, onStageMouseLeave, false, 0, true);
        }

        public static function detachListeners(
            stageSpace:Stage,
            onStageResize:Function,
            onStageMouseMove:Function,
            onStageMouseLeave:Function
        ):void {
            if (stageSpace == null) {
                return;
            }

            stageSpace.removeEventListener(Event.RESIZE, onStageResize);
            stageSpace.removeEventListener(MouseEvent.MOUSE_MOVE, onStageMouseMove);
            stageSpace.removeEventListener(Event.MOUSE_LEAVE, onStageMouseLeave);
        }

        public static function updateTrackedStageSize(
            stageSpace:Stage,
            lastStageWidth:Number,
            lastStageHeight:Number
        ):Object {
            var stageWidth:Number;
            var stageHeight:Number;

            if (stageSpace == null) {
                return {
                    changed: false,
                    stageWidth: lastStageWidth,
                    stageHeight: lastStageHeight
                };
            }

            stageWidth = stageSpace.stageWidth;
            stageHeight = stageSpace.stageHeight;
            return {
                changed: stageWidth != lastStageWidth || stageHeight != lastStageHeight,
                stageWidth: stageWidth,
                stageHeight: stageHeight
            };
        }

        public static function resolveBarLayout(stageSpace:Stage):Object {
            if (stageSpace == null) {
                return ResearchProgressBarLayout.defaultLayout();
            }

            return ResearchProgressBarLayout.calculate(stageSpace.stageWidth, stageSpace.stageHeight);
        }
    }
}