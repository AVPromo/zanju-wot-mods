package {
    import flash.display.Shape;
    import flash.display.Sprite;
    import flash.events.Event;
    import flash.geom.Matrix;
    import flash.text.TextField;
    import flash.text.TextFieldAutoSize;
    import flash.text.TextFormat;
    import net.wg.infrastructure.base.AbstractView;

    [SWF(width="1920", height="1080", frameRate="30", backgroundColor="#000000")]
    public class PremiumTimeLobby extends AbstractView {
        private static const PANEL_WIDTH:Number = 230;
        private static const PADDING:Number = 10;
        private static const TITLE_HEIGHT:Number = 22;
        private static const ROW_HEIGHT:Number = 20;
        private static const EDGE_MARGIN:Number = 14;
        private static const LABEL_RATIO:Number = 0.62;
        private static const FONT_NAME:String = "Arial";

        private static const LABEL_COLOR:uint = 0xE6DDC8;
        private static const TITLE_COLOR:uint = 0xFFFFFF;
        private static const SEVERITY_NORMAL:uint = 0x9FD17A;
        private static const SEVERITY_WARNING:uint = 0xF0C850;
        private static const SEVERITY_CRITICAL:uint = 0xE85C4A;
        private static const SEVERITY_INACTIVE:uint = 0x9A9A9A;

        private var panel:Sprite;
        private var background:Shape;
        private var titleField:TextField;
        private var rowsContainer:Sprite;
        private var _context:Object;
        private var _corner:String = "top_right";
        private var _lineCount:int = 0;
        private var _isReady:Boolean = false;
        private var _lastStageWidth:Number = -1;
        private var _lastStageHeight:Number = -1;
        private var _lastEffectiveScale:Number = -1;

        public function PremiumTimeLobby() {
            super();
        }

        override protected function configUI():void {
            super.configUI();
            visible = false;
            mouseEnabled = false;
            mouseChildren = false;
            build();
            removeEventListener(Event.ENTER_FRAME, onEnterFrame);
            addEventListener(Event.ENTER_FRAME, onEnterFrame, false, 0, true);
        }

        override protected function onDispose():void {
            removeEventListener(Event.ENTER_FRAME, onEnterFrame);
            if (stage != null) {
                stage.removeEventListener(Event.RESIZE, onStageResize);
            }
            super.onDispose();
        }

        override protected function nextFrameAfterPopulateHandler():void {
            super.nextFrameAfterPopulateHandler();
            _isReady = true;
            if (stage != null) {
                stage.removeEventListener(Event.RESIZE, onStageResize);
                stage.addEventListener(Event.RESIZE, onStageResize, false, 0, true);
            }
            // Render any context that arrived before the display objects were built.
            applyContext();
        }

        private function build():void {
            panel = new Sprite();
            panel.mouseEnabled = false;
            panel.mouseChildren = false;
            addChild(panel);

            background = new Shape();
            panel.addChild(background);

            titleField = createField(13, true, TITLE_COLOR, "left");
            panel.addChild(titleField);

            rowsContainer = new Sprite();
            rowsContainer.mouseEnabled = false;
            rowsContainer.mouseChildren = false;
            panel.addChild(rowsContainer);
        }

        private function createField(size:int, bold:Boolean, color:uint, align:String):TextField {
            var field:TextField = new TextField();
            field.selectable = false;
            field.mouseEnabled = false;
            field.embedFonts = false;
            field.autoSize = TextFieldAutoSize.NONE;
            field.defaultTextFormat = makeFormat(size, bold, color, align);
            return field;
        }

        private function makeFormat(size:int, bold:Boolean, color:uint, align:String):TextFormat {
            var format:TextFormat = new TextFormat();
            format.font = FONT_NAME;
            format.size = size;
            format.bold = bold;
            format.color = color;
            format.align = align;
            return format;
        }

        public function as_setContext(data:Object):void {
            _context = data;
            if (data != null && data.corner != null) {
                _corner = String(data.corner);
            }
            applyContext();
        }

        private function applyContext():void {
            // as_setContext can arrive before configUI()/build() has created the text
            // fields (the SWF pushes a load callback before its first frame is ready).
            // Defer until nextFrameAfterPopulateHandler flips _isReady, which then replays
            // the stored context.
            if (!_isReady) {
                return;
            }
            renderContext();
            relayout();
        }

        public function as_setVisible(value:Boolean):void {
            visible = value;
        }

        public function as_ping():String {
            return "premium-time-lobby-ready";
        }

        public function as_refreshLayout():void {
            relayout();
        }

        private function renderContext():void {
            titleField.text = _context != null && _context.title != null ? String(_context.title) : "";

            while (rowsContainer.numChildren > 0) {
                rowsContainer.removeChildAt(0);
            }

            var lines:Array = _context != null && _context.lines is Array ? _context.lines as Array : [];
            var rowWidth:Number = PANEL_WIDTH - PADDING * 2;
            _lineCount = lines.length;

            var i:int;
            for (i = 0; i < lines.length; i++) {
                var line:Object = lines[i];

                var labelField:TextField = createField(13, false, LABEL_COLOR, "left");
                labelField.width = rowWidth * LABEL_RATIO;
                labelField.height = ROW_HEIGHT;
                labelField.x = 0;
                labelField.y = i * ROW_HEIGHT;
                labelField.text = line != null && line.label != null ? String(line.label) : "";
                rowsContainer.addChild(labelField);

                var valueField:TextField = createField(13, true, severityColor(line), "right");
                valueField.width = rowWidth * (1 - LABEL_RATIO);
                valueField.height = ROW_HEIGHT;
                valueField.x = rowWidth * LABEL_RATIO;
                valueField.y = i * ROW_HEIGHT;
                valueField.text = line != null && line.value != null ? String(line.value) : "";
                rowsContainer.addChild(valueField);
            }
        }

        private function severityColor(line:Object):uint {
            var severity:String = line != null && line.severity != null ? String(line.severity) : "normal";
            switch (severity) {
                case "critical":
                case "expired":
                    return SEVERITY_CRITICAL;
                case "warning":
                    return SEVERITY_WARNING;
                case "inactive":
                    return SEVERITY_INACTIVE;
                default:
                    return SEVERITY_NORMAL;
            }
        }

        private function relayout():void {
            if (!_isReady || stage == null) {
                return;
            }

            var bodyHeight:Number = TITLE_HEIGHT + _lineCount * ROW_HEIGHT;
            var panelHeight:Number = PADDING * 2 + bodyHeight;

            background.graphics.clear();
            background.graphics.beginFill(0x000000, 0.55);
            background.graphics.drawRoundRect(0, 0, PANEL_WIDTH, panelHeight, 10, 10);
            background.graphics.endFill();

            titleField.x = PADDING;
            titleField.y = PADDING;
            titleField.width = PANEL_WIDTH - PADDING * 2;
            titleField.height = TITLE_HEIGHT;

            rowsContainer.x = PADDING;
            rowsContainer.y = PADDING + TITLE_HEIGHT;

            anchorPanel(panelHeight);

            _lastEffectiveScale = resolveEffectiveScale();
            _lastStageWidth = stage.stageWidth;
            _lastStageHeight = stage.stageHeight;
        }

        private function anchorPanel(panelHeight:Number):void {
            var scale:Number = resolveEffectiveScale();
            var logicalWidth:Number = stage.stageWidth / scale;
            var logicalHeight:Number = stage.stageHeight / scale;
            var anchorLeft:Boolean = _corner == "top_left" || _corner == "bottom_left";
            var anchorTop:Boolean = _corner == "top_left" || _corner == "top_right";

            panel.x = anchorLeft ? EDGE_MARGIN : (logicalWidth - PANEL_WIDTH - EDGE_MARGIN);
            panel.y = anchorTop ? EDGE_MARGIN : (logicalHeight - panelHeight - EDGE_MARGIN);
        }

        private function resolveEffectiveScale():Number {
            var concatenated:Matrix = transform.concatenatedMatrix;
            var scale:Number = concatenated != null ? concatenated.a : 1;
            if (!(scale > 0)) {
                scale = 1;
            }
            return scale;
        }

        private function onStageResize(event:Event):void {
            relayout();
        }

        private function onEnterFrame(event:Event):void {
            if (!_isReady || stage == null) {
                return;
            }
            var scale:Number = resolveEffectiveScale();
            if (stage.stageWidth == _lastStageWidth
                && stage.stageHeight == _lastStageHeight
                && scale == _lastEffectiveScale) {
                return;
            }
            relayout();
        }
    }
}
