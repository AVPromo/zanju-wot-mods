package
{
    import flash.display.Shape;
    import flash.display.Sprite;
    import flash.events.MouseEvent;
    import flash.geom.Rectangle;
    import flash.text.TextField;
    import flash.text.TextFormat;
    import net.wg.infrastructure.base.AbstractView;

    [SWF(width="420", height="180", frameRate="30", backgroundColor="#000000")]
    public class ResearchProgressBarLobby extends AbstractView
    {
        private static const PANEL_WIDTH:Number = 420;
        private static const PANEL_HEIGHT:Number = 180;
        private static const HEADER_HEIGHT:Number = 34;
        private static const BAR_WIDTH:Number = 372;
        private static const BAR_HEIGHT:Number = 16;

        private var background:Shape;
        private var header:Sprite;
        private var headerTitle:TextField;
        private var vehicleLabel:TextField;
        private var summaryLabel:TextField;
        private var detailLabel:TextField;
        private var progressTrack:Shape;
        private var progressFill:Shape;
        private var progressLabel:TextField;
        private var metricLeft:TextField;
        private var metricRight:TextField;
        private var iconStrip:Sprite;

        public function ResearchProgressBarLobby()
        {
            super();
        }

        override protected function configUI():void
        {
            super.configUI();
            mouseEnabled = true;
            mouseChildren = true;
            build();
            applyContext({
                title: "Research Progress",
                vehicle: "TVP T 50/51",
                summary: "Tech tree: 72% toward next unlock",
                detail: "Field mods: 3/6 steps unlocked",
                progress: 72,
                leftMetric: "32,450 XP",
                rightMetric: "Next unlock: 45,000 XP"
            });
        }

        override protected function onDispose():void
        {
            if (header != null)
            {
                header.removeEventListener(MouseEvent.MOUSE_DOWN, onHeaderMouseDown);
            }
            if (stage != null)
            {
                stage.removeEventListener(MouseEvent.MOUSE_UP, onStageMouseUp);
            }
            super.onDispose();
        }

        private function build():void
        {
            background = new Shape();
            addChild(background);

            header = new Sprite();
            header.buttonMode = true;
            header.useHandCursor = true;
            header.addEventListener(MouseEvent.MOUSE_DOWN, onHeaderMouseDown);
            addChild(header);

            headerTitle = makeTextField(18, 8, 220, 20, 0xF4F0E8, 16, true);
            header.addChild(headerTitle);

            vehicleLabel = makeTextField(24, 48, 372, 20, 0xF4F0E8, 18, true);
            addChild(vehicleLabel);

            summaryLabel = makeTextField(24, 74, 372, 18, 0xD7D2C7, 13, false);
            addChild(summaryLabel);

            detailLabel = makeTextField(24, 96, 372, 18, 0xAAA69A, 12, false);
            addChild(detailLabel);

            progressTrack = new Shape();
            progressTrack.x = 24;
            progressTrack.y = 124;
            addChild(progressTrack);

            progressFill = new Shape();
            progressFill.x = 24;
            progressFill.y = 124;
            addChild(progressFill);

            progressLabel = makeTextField(24, 144, 100, 18, 0xF4F0E8, 12, true);
            addChild(progressLabel);

            metricLeft = makeTextField(24, 144, 160, 18, 0xD7D2C7, 12, false);
            addChild(metricLeft);

            metricRight = makeTextField(200, 144, 196, 18, 0xD7D2C7, 12, false);
            metricRight.autoSize = "right";
            metricRight.x = 200;
            addChild(metricRight);

            iconStrip = new Sprite();
            iconStrip.x = 320;
            iconStrip.y = 14;
            addChild(iconStrip);

            drawIcons();
            drawChrome();
        }

        public function as_setContext(data:Object):void
        {
            applyContext(data);
        }

        public function as_setProgress(value:Number):void
        {
            updateProgress(value);
        }

        public function as_ping():String
        {
            return "research-progress-bar-lobby-ready";
        }

        private function applyContext(data:Object):void
        {
            if (data == null)
            {
                return;
            }

            if (data.title !== undefined)
            {
                headerTitle.text = String(data.title);
            }
            if (data.vehicle !== undefined)
            {
                vehicleLabel.text = String(data.vehicle);
            }
            if (data.summary !== undefined)
            {
                summaryLabel.text = String(data.summary);
            }
            if (data.detail !== undefined)
            {
                detailLabel.text = String(data.detail);
            }
            if (data.leftMetric !== undefined)
            {
                metricLeft.text = String(data.leftMetric);
            }
            if (data.rightMetric !== undefined)
            {
                metricRight.text = String(data.rightMetric);
            }
            if (data.progress !== undefined)
            {
                updateProgress(Number(data.progress));
            }
        }

        private function updateProgress(value:Number):void
        {
            var clamped:Number = Math.max(0, Math.min(100, value));

            progressFill.graphics.clear();
            progressFill.graphics.beginFill(0xC38C39, 1.0);
            progressFill.graphics.drawRoundRect(0, 0, BAR_WIDTH * clamped / 100.0, BAR_HEIGHT, 8, 8);
            progressFill.graphics.endFill();

            progressLabel.text = int(clamped).toString() + "%";
        }

        private function drawChrome():void
        {
            background.graphics.clear();
            background.graphics.beginFill(0x171411, 0.92);
            background.graphics.drawRoundRect(0, 0, PANEL_WIDTH, PANEL_HEIGHT, 14, 14);
            background.graphics.endFill();

            background.graphics.lineStyle(1, 0x4D4032, 1.0);
            background.graphics.drawRoundRect(0.5, 0.5, PANEL_WIDTH - 1, PANEL_HEIGHT - 1, 14, 14);

            header.graphics.clear();
            header.graphics.beginFill(0x2A221A, 0.98);
            header.graphics.drawRoundRect(0, 0, PANEL_WIDTH, HEADER_HEIGHT, 14, 14);
            header.graphics.endFill();

            header.graphics.beginFill(0x2A221A, 0.98);
            header.graphics.drawRect(0, HEADER_HEIGHT - 14, PANEL_WIDTH, 14);
            header.graphics.endFill();

            progressTrack.graphics.clear();
            progressTrack.graphics.beginFill(0x0F0D0B, 1.0);
            progressTrack.graphics.drawRoundRect(0, 0, BAR_WIDTH, BAR_HEIGHT, 8, 8);
            progressTrack.graphics.endFill();

            progressTrack.graphics.lineStyle(1, 0x5B4E3F, 1.0);
            progressTrack.graphics.drawRoundRect(0, 0, BAR_WIDTH, BAR_HEIGHT, 8, 8);
        }

        private function drawIcons():void
        {
            var colors:Array = [0xC38C39, 0x8AA7B1, 0x6C9B5C];
            var index:int;
            for (index = 0; index < colors.length; index++)
            {
                var dot:Shape = new Shape();
                dot.graphics.beginFill(colors[index], 1.0);
                dot.graphics.drawCircle(0, 0, 7);
                dot.graphics.endFill();
                dot.x = index * 22;
                dot.y = 7;
                iconStrip.addChild(dot);
            }
        }

        private function onHeaderMouseDown(event:MouseEvent):void
        {
            if (stage == null)
            {
                return;
            }

            startDrag(false, getDragBounds());
            stage.addEventListener(MouseEvent.MOUSE_UP, onStageMouseUp);
        }

        private function onStageMouseUp(event:MouseEvent):void
        {
            stopDrag();
            if (stage != null)
            {
                stage.removeEventListener(MouseEvent.MOUSE_UP, onStageMouseUp);
            }
        }

        private function getDragBounds():Rectangle
        {
            if (stage == null)
            {
                return new Rectangle(0, 0, PANEL_WIDTH, PANEL_HEIGHT);
            }

            return new Rectangle(
                0,
                0,
                Math.max(0, stage.stageWidth - PANEL_WIDTH),
                Math.max(0, stage.stageHeight - PANEL_HEIGHT)
            );
        }

        private function makeTextField(
            posX:Number,
            posY:Number,
            width:Number,
            height:Number,
            color:uint,
            size:int,
            bold:Boolean
        ):TextField
        {
            var field:TextField = new TextField();
            field.defaultTextFormat = new TextFormat("_sans", size, color, bold);
            field.x = posX;
            field.y = posY;
            field.width = width;
            field.height = height;
            field.selectable = false;
            field.mouseEnabled = false;
            field.textColor = color;
            return field;
        }
    }
}