package {
    import flash.text.AntiAliasType;
    import flash.text.TextField;

    public final class ResearchProgressBarFonts {
        [Embed(source="assets/fonts/RobotoMono-Regular.ttf", fontName="ResearchProgressBarFont", mimeType="application/x-font-truetype", embedAsCFF="false", unicodeRange="U+0020-U+007E")]
        private static const ROBOTO_MONO_REGULAR:Class;

        [Embed(source="assets/fonts/RobotoMono-Bold.ttf", fontName="ResearchProgressBarFont", mimeType="application/x-font-truetype", embedAsCFF="false", fontWeight="bold", unicodeRange="U+0020-U+007E")]
        private static const ROBOTO_MONO_BOLD:Class;

        public static const FONT_NAME:String = "ResearchProgressBarFont";

        public static function configureTextField(field:TextField):TextField {
            field.embedFonts = true;
            field.antiAliasType = AntiAliasType.ADVANCED;
            return field;
        }
    }
}