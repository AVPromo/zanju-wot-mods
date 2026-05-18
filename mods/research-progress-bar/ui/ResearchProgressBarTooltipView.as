package {
    import flash.display.DisplayObject;
    import flash.display.Shape;
    import flash.display.Sprite;
    import flash.display.Stage;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;

    public final class ResearchProgressBarTooltipView {
        private static const TOOLTIP_BACKGROUND_COLOR:uint = 0x0B0B0B;
        private static const TOOLTIP_BACKGROUND_ALPHA:Number = 0.93;
        private static const TOOLTIP_BORDER_COLOR:uint = 0x7A6954;
        private static const TOOLTIP_PADDING_X:Number = 8;
        private static const TOOLTIP_PADDING_Y:Number = 6;
        private static const TOOLTIP_PADDING_BOTTOM:Number = 8;
        private static const TOOLTIP_OFFSET_Y:Number = 15;

        public static function showEntries(
            tooltipContainer:Sprite,
            tooltipBackground:Shape,
            tooltipContent:Sprite,
            entries:Array,
            stageX:Number,
            stageY:Number,
            stageWidth:Number,
            stageHeight:Number
        ):void {
            var entry:Object;
            var section:Sprite;
            var sectionBounds:Rectangle;
            var contentBounds:Rectangle;
            var cursorY:Number = 0;
            var idx:int;
            var tooltipWidth:Number;
            var tooltipHeight:Number;

            if (tooltipContainer == null || tooltipBackground == null || tooltipContent == null) {
                return;
            }

            clearContent(tooltipContent);

            for (idx = 0; idx < entries.length; idx++) {
                entry = entries[idx];
                section = ResearchProgressBarTooltipContent.buildTooltipSection(entry);
                section.y = cursorY;
                tooltipContent.addChild(section);
                sectionBounds = section.getBounds(section);
                cursorY += sectionBounds.height;
                if (idx < entries.length - 1) {
                    cursorY += ResearchProgressBarTooltipContent.SECTION_GAP;
                }
            }

            contentBounds = tooltipContent.getBounds(tooltipContent);
            tooltipContent.x = TOOLTIP_PADDING_X - contentBounds.x;
            tooltipContent.y = TOOLTIP_PADDING_Y - contentBounds.y;

            tooltipWidth = contentBounds.width + TOOLTIP_PADDING_X * 2;
            tooltipHeight = contentBounds.height + TOOLTIP_PADDING_Y + TOOLTIP_PADDING_BOTTOM;
            drawBackground(tooltipBackground, tooltipWidth, tooltipHeight);

            tooltipContainer.visible = true;
            positionContainer(tooltipContainer, stageX, stageY, tooltipWidth, tooltipHeight, stageWidth, stageHeight);
        }

        public static function hideTooltip(tooltipContainer:Sprite):void {
            if (tooltipContainer != null) {
                tooltipContainer.visible = false;
            }
        }

        public static function refreshAtStagePoint(
            hostVisible:Boolean,
            markersContainer:Sprite,
            tooltipDataByDisplay:Dictionary,
            tooltipContainer:Sprite,
            tooltipBackground:Shape,
            tooltipContent:Sprite,
            stageSpace:Stage,
            stageX:Number,
            stageY:Number
        ):void {
            var tooltipEntries:Array;

            if (!hostVisible || markersContainer == null) {
                hideTooltip(tooltipContainer);
                return;
            }

            tooltipEntries = resolveEntriesAtStagePoint(
                markersContainer,
                tooltipDataByDisplay,
                stageSpace,
                stageX,
                stageY
            );

            if (tooltipEntries.length == 0) {
                hideTooltip(tooltipContainer);
                return;
            }

            showEntries(
                tooltipContainer,
                tooltipBackground,
                tooltipContent,
                tooltipEntries,
                stageX,
                stageY,
                stageSpace != null ? stageSpace.stageWidth : NaN,
                stageSpace != null ? stageSpace.stageHeight : NaN
            );
        }

        public static function resolveEntriesAtStagePoint(
            markersContainer:Sprite,
            tooltipDataByDisplay:Dictionary,
            stageSpace:DisplayObject,
            stageX:Number,
            stageY:Number
        ):Array {
            var entries:Array = [];
            var candidate:Sprite;
            var candidateBounds:Rectangle;
            var candidateData:Object;
            var idx:int;

            if (markersContainer == null || tooltipDataByDisplay == null || stageSpace == null) {
                return entries;
            }

            for (idx = 0; idx < markersContainer.numChildren; idx++) {
                candidate = markersContainer.getChildAt(idx) as Sprite;
                if (candidate == null) {
                    continue;
                }

                candidateBounds = candidate.getBounds(stageSpace);
                if (candidateBounds == null || !candidateBounds.contains(stageX, stageY)) {
                    continue;
                }

                candidateData = tooltipDataByDisplay[candidate];
                if (candidateData != null) {
                    entries.push(candidateData);
                }
            }

            return entries;
        }

        private static function clearContent(tooltipContent:Sprite):void {
            if (tooltipContent == null) {
                return;
            }

            while (tooltipContent.numChildren > 0) {
                tooltipContent.removeChildAt(0);
            }
        }

        private static function positionContainer(
            tooltipContainer:Sprite,
            stageX:Number,
            stageY:Number,
            tooltipWidth:Number,
            tooltipHeight:Number,
            stageWidth:Number,
            stageHeight:Number
        ):void {
            var tooltipX:Number = stageX - Math.round(tooltipWidth / 2);
            var tooltipY:Number = stageY + TOOLTIP_OFFSET_Y;
            var minX:Number = 4;
            var maxX:Number;
            var minY:Number = 4;
            var maxY:Number;

            if (!isNaN(stageWidth) && !isNaN(stageHeight)) {
                maxX = stageWidth - tooltipWidth - 4;
                maxY = stageHeight - tooltipHeight - 4;
                if (tooltipX < minX) {
                    tooltipX = minX;
                }
                if (tooltipX > maxX) {
                    tooltipX = maxX;
                }

                if (tooltipY > maxY) {
                    tooltipY = stageY - tooltipHeight - TOOLTIP_OFFSET_Y;
                }

                if (tooltipY < minY) {
                    tooltipY = minY;
                }
                if (tooltipY > maxY) {
                    tooltipY = maxY;
                }
            }

            tooltipContainer.x = Math.round(tooltipX);
            tooltipContainer.y = Math.round(tooltipY);
        }

        private static function drawBackground(tooltipBackground:Shape, width:Number, height:Number):void {
            tooltipBackground.graphics.clear();
            tooltipBackground.graphics.lineStyle(1, TOOLTIP_BORDER_COLOR, 1.0);
            tooltipBackground.graphics.beginFill(TOOLTIP_BACKGROUND_COLOR, TOOLTIP_BACKGROUND_ALPHA);
            tooltipBackground.graphics.drawRoundRect(0, 0, width, height, 6, 6);
            tooltipBackground.graphics.endFill();
        }
    }
}