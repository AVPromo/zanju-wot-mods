package net.wg.infrastructure.base {
    import flash.display.InteractiveObject;
    import flash.display.MovieClip;

    public class AbstractView extends MovieClip {
        public function AbstractView() {
            super();
        }

        protected function configUI():void {
        }

        protected function onDispose():void {
        }

        protected function nextFrameAfterPopulateHandler():void {
        }

        // Compile-time stub of WG's AbstractView.setFocus. At runtime the real
        // AbstractView (which manages modal focus and _lastFocusedElement) runs.
        protected function setFocus(target:InteractiveObject):void {
        }
    }
}
