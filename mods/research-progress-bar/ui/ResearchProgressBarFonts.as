package {
    import flash.text.AntiAliasType;
    import flash.text.TextField;
    import flash.text.TextFormat;

    public final class ResearchProgressBarFonts {
        [Embed(source="assets/fonts/RobotoMono-Regular.ttf", fontName="ResearchProgressBarFont", mimeType="application/x-font-truetype", embedAsCFF="false", unicodeRange="U+0020-U+007E,U+00A0-U+017F,U+0400-U+04FF,U+2013-U+2014")]
        private static const ROBOTO_MONO_REGULAR:Class;

        [Embed(source="assets/fonts/RobotoMono-Bold.ttf", fontName="ResearchProgressBarFont", mimeType="application/x-font-truetype", embedAsCFF="false", fontWeight="bold", unicodeRange="U+0020-U+007E,U+00A0-U+017F,U+0400-U+04FF,U+2013-U+2014")]
        private static const ROBOTO_MONO_BOLD:Class;

        public static const FONT_NAME:String = "ResearchProgressBarFont";
        // Device font used when text contains characters outside the embedded unicode ranges
        // (Latin and Cyrillic are embedded; this path covers the rest, e.g. Greek and CJK).
        // "_sans" resolves to the OS default sans (Arial on Windows), which has Latin/Greek/Cyrillic
        // coverage but NO Korean glyphs — Korean rendered as boxes. Malgun Gothic ships with every
        // Windows install (all locales, since Vista) and covers Latin + Greek + Cyrillic + Hangul,
        // so it renders Korean correctly.
        public static const FALLBACK_FONT_NAME:String = "Malgun Gothic";

        public static function configureTextField(field:TextField):TextField {
            field.embedFonts = true;
            field.antiAliasType = AntiAliasType.ADVANCED;
            return field;
        }

        // Assigns plain text to a field, automatically selecting the embedded font when every
        // character is in the embedded range, or the device fallback font when any character is
        // outside it. This is the single entry point for rendering dynamic/localised text so the
        // fallback applies everywhere, not just in tooltips.
        public static function setText(field:TextField, text:String):void {
            var value:String = text == null ? "" : text;
            applyContentFont(field, containsNonEmbeddedChars(value));
            field.text = value;
        }

        // Like setText, but for HTML-formatted content assigned to field.htmlText. Detection also
        // accounts for &#xXXXX; numeric entities (see htmlContainsNonEmbeddedChars).
        public static function setHtmlText(field:TextField, html:String):void {
            var value:String = html == null ? "" : html;
            applyContentFont(field, htmlContainsNonEmbeddedChars(value));
            field.htmlText = value;
        }

        // Switches a field between the embedded font and the device fallback font. The fallback
        // path disables font embedding (the device font has no embedded glyphs) and uses NORMAL
        // anti-aliasing, since ADVANCED only applies to embedded fonts. Size/colour/bold already
        // present on the field's defaultTextFormat are preserved.
        private static function applyContentFont(field:TextField, useFallback:Boolean):void {
            var format:TextFormat = field.defaultTextFormat;
            if (useFallback) {
                field.embedFonts = false;
                field.antiAliasType = AntiAliasType.NORMAL;
                format.font = FALLBACK_FONT_NAME;
            } else {
                field.embedFonts = true;
                field.antiAliasType = AntiAliasType.ADVANCED;
                format.font = FONT_NAME;
            }
            field.defaultTextFormat = format;
        }

        // Returns true if any character in text falls outside the ranges embedded in ROBOTO_MONO_*.
        // Embedded ranges: U+0020-U+007E (Basic Latin), U+00A0-U+017F (Latin-1 + Latin Extended-A),
        // U+0400-U+04FF (Cyrillic), U+2013-U+2014 (en/em dash). Keep in sync with the [Embed]
        // unicodeRange attributes above.
        private static function containsNonEmbeddedChars(text:String):Boolean {
            if (text == null || text.length == 0) {
                return false;
            }

            var i:int;
            var code:int;
            for (i = 0; i < text.length; i++) {
                code = text.charCodeAt(i);
                if (code < 0x0020) {
                    continue;
                }
                if (code <= 0x007E) {
                    continue;
                }
                if (code < 0x00A0) {
                    return true;
                }
                if (code <= 0x017F) {
                    continue;
                }
                if (code < 0x0400) {
                    return true;
                }
                if (code <= 0x04FF) {
                    continue;
                }
                if (code < 0x2013) {
                    return true;
                }
                if (code <= 0x2014) {
                    continue;
                }
                return true;
            }
            return false;
        }

        // Like containsNonEmbeddedChars but also parses HTML numeric entities (&#xXXXX; form).
        // Use this for strings that will be assigned to field.htmlText, since Python encodes
        // non-ASCII as entities to survive the WoT Python→Scaleform bridge.
        private static function htmlContainsNonEmbeddedChars(html:String):Boolean {
            if (html == null || html.length == 0) {
                return false;
            }

            if (containsNonEmbeddedChars(html)) {
                return true;
            }

            var idx:int = 0;
            var eIdx:int;
            var semiIdx:int;
            var code:int;

            while (true) {
                eIdx = html.indexOf("&#x", idx);
                if (eIdx < 0) {
                    break;
                }
                semiIdx = html.indexOf(";", eIdx + 3);
                if (semiIdx < 0) {
                    break;
                }
                code = parseInt(html.substring(eIdx + 3, semiIdx), 16);
                if (code > 0x017F
                        && !(code >= 0x0400 && code <= 0x04FF)
                        && !(code >= 0x2013 && code <= 0x2014)) {
                    return true;
                }
                idx = semiIdx + 1;
            }
            return false;
        }
    }
}