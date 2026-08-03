<?php
/**
 * Plugin Name: המקום — <שם העמוד> · <תיאור קצר>
 * Description: עמוד נתונים אינטראקטיבי (scrollytelling). מוטמע ב-iframe מבודד — אינו משפיע על עיצוב התבנית ואינו מושפע ממנה. שורטקוד: [SHORTCODE]
 * Version: 1.0.0
 * Author: המקום הכי חם בגיהנום
 *
 * === איך משכפלים לעמוד חדש ===
 *   1. שנה את שם הקובץ ושם התיקייה (למשל hamakom-<slug>/hamakom-<slug>.php).
 *   2. החלף בכל הקובץ: SHORTCODE → שם השורטקוד (למשל hamakom_<slug>),
 *      ו-hmk_data_ → קידומת ייחודית (למשל hmk_<slug>_).
 *   3. שים את העמוד תחת app/index.html + נתונים + vendor/leaflet (Leaflet מקומי, לא CDN).
 *
 * iframe ולא scoping: בידוד CSS/JS מוחלט מול JNews/WPBakery/WP-Rocket (אפס מלחמות
 * !important), ושטח תקיפה = קובץ סטטי (אין DB, אין קלט משתמש, אין PHP דינמי מעבר
 * לפליטת iframe אחד עם esc_url()).
 *
 * @package hamakom-data-page
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // No direct access.
}

if ( ! function_exists( 'hmk_data_shortcode' ) ) :
	/**
	 * Render the [SHORTCODE] embed.
	 *
	 * @param array $atts Optional: height (CSS value, default "100vh"),
	 *                    fullbleed ("1"/"0", default "1").
	 * @return string
	 */
	function hmk_data_shortcode( $atts ) {

		$atts = shortcode_atts(
			array(
				'height'    => '100vh',
				'fullbleed' => '1',
			),
			$atts,
			'SHORTCODE'
		);

		// Sanitize the height to a safe CSS length/keyword (digits + unit only).
		$height = preg_replace( '/[^0-9a-z%.]/i', '', (string) $atts['height'] );
		if ( '' === $height ) {
			$height = '100vh';
		}

		$src       = esc_url( plugins_url( 'app/index.html', __FILE__ ) );
		$fullbleed = ( '1' === (string) $atts['fullbleed'] );

		// Unique id so multiple embeds / repeated CSS never collide.
		static $n = 0;
		$n++;
		$id = 'hmk-data-embed-' . $n;

		$wrap_style = 'margin:0;padding:0;';
		if ( $fullbleed ) {
			// Break out of the theme's centered content column, edge-to-edge.
			$wrap_style .= 'width:100vw;max-width:100vw;position:relative;left:50%;right:50%;margin-left:-50vw;margin-right:-50vw;';
		} else {
			$wrap_style .= 'width:100%;';
		}

		ob_start();
		?>
		<div id="<?php echo esc_attr( $id ); ?>" class="hmk-data-embed" style="<?php echo esc_attr( $wrap_style ); ?>">
			<iframe
				src="<?php echo $src; // already esc_url'd ?>"
				title="<עמוד נתונים — המקום>"
				loading="lazy"
				scrolling="yes"
				sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"
				referrerpolicy="no-referrer-when-downgrade"
				style="display:block;width:100%;height:<?php echo esc_attr( $height ); ?>;border:0;margin:0;background:#faf9f5;"
			></iframe>
		</div>
		<style>
			#<?php echo esc_attr( $id ); ?> iframe{height:<?php echo esc_attr( $height ); ?>;}
			@supports (height:100dvh){#<?php echo esc_attr( $id ); ?> iframe{height:100dvh;}}
		</style>
		<?php
		return ob_get_clean();
	}
	add_shortcode( 'SHORTCODE', 'hmk_data_shortcode' );
endif;
