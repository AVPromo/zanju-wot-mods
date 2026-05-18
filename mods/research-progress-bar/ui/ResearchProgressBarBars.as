package {
    import flash.display.Bitmap;
    import flash.display.Shape;

    public final class ResearchProgressBarBars {
        public static function render(
            baseBar:Bitmap,
            completedBar:Bitmap,
            combatBar:Bitmap,
            freeBar:Bitmap,
            completedMaskShape:Shape,
            combatMaskShape:Shape,
            freeMaskShape:Shape,
            barX:Number,
            barY:Number,
            barWidth:Number,
            barHeight:Number,
            fillState:Object,
            completedOnly:Boolean
        ):void {
            baseBar.visible = true;
            completedBar.visible = true;
            combatBar.visible = !completedOnly;
            freeBar.visible = !completedOnly;

            applyBounds(baseBar, barX, barY, barWidth, barHeight);
            applyBounds(completedBar, barX, barY, barWidth, barHeight);
            applyBounds(combatBar, barX, barY, barWidth, barHeight);
            applyBounds(freeBar, barX, barY, barWidth, barHeight);

            drawMask(completedMaskShape, barX, barY, Number(fillState.completedWidth), barHeight);
            drawMask(
                combatMaskShape,
                barX + Number(fillState.completedWidth),
                barY,
                Number(fillState.primaryWidth),
                barHeight
            );
            drawMask(
                freeMaskShape,
                barX + Number(fillState.completedWidth) + Number(fillState.primaryWidth),
                barY,
                Number(fillState.secondaryWidth),
                barHeight
            );
        }

        public static function clear(
            baseBar:Bitmap,
            completedBar:Bitmap,
            combatBar:Bitmap,
            freeBar:Bitmap,
            completedMaskShape:Shape,
            combatMaskShape:Shape,
            freeMaskShape:Shape,
            barX:Number,
            barY:Number,
            barHeight:Number
        ):void {
            drawMask(completedMaskShape, barX, barY, 0, barHeight);
            drawMask(combatMaskShape, barX, barY, 0, barHeight);
            drawMask(freeMaskShape, barX, barY, 0, barHeight);
            baseBar.visible = false;
            completedBar.visible = false;
            combatBar.visible = false;
            freeBar.visible = false;
        }

        private static function applyBounds(bitmap:Bitmap, posX:Number, posY:Number, width:Number, height:Number):void {
            bitmap.x = posX;
            bitmap.y = posY;
            bitmap.width = width;
            bitmap.height = height;
        }

        private static function drawMask(shape:Shape, posX:Number, posY:Number, width:Number, height:Number):void {
            shape.graphics.clear();
            if (width <= 0 || height <= 0) {
                return;
            }

            shape.graphics.beginFill(0xFFFFFF, 1.0);
            shape.graphics.drawRect(posX, posY, width, height);
            shape.graphics.endFill();
        }
    }
}