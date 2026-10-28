# Welcome screen and title identity

The welcome screen takes its sparse navigation, dark interior framing and restrained red selection treatment from the user-selected Home Sweet Home reference. The artwork, title lettering and thread motif are original to The Unbroken Debt. Cambodian architecture, Khmer title and the existing Episode I identity are preserved. The serif title is an intentional departure from the earlier Ubuntu Bold art-bible direction, requested by the user.

Reference: https://www.mobygames.com/game/96548/home-sweet-home/screenshots/windows/960273/

## Assets

- `public/assets/ui/unbroken-debt-logo.png`: transparent title lockup, including the red binding-thread motif.
- `public/assets/ui/welcome-house.jpg`: illustrated title background, converted to JPEG for delivery.

Both assets were created with the built-in OpenAI image generation tool. The background uses an illustration with a brief arrival fade rather than the live funeral-tent scene proposed in the original interface document. Reduced-motion preferences remove the fade.

## Behavior

The default URL opens the title screen before hardware detection and game initialization. New game starts the prologue; Continue uses the existing IndexedDB autosave and checkpoint loader. Unreadable or unavailable saves receive a visible status message. Restarting with an existing save asks for confirmation inside the game. Settings persist sound, mouse sensitivity and inverted vertical look; changes apply at startup. Settings remain usable for the current session if local storage is unavailable. Arrow keys, Home/End, Tab and Enter support menu navigation. Dialogs use native focus management and Escape dismissal. Fullscreen is requested only when its button is clicked.

Existing `?start=act1`, `?continue` and recognized spike URLs retain their direct entry behavior. The engine's existing requirements page still handles unsupported devices. Game loading failures show a return-to-title action. The in-game listening screen handles pointer capture and audio unlock when the player presses Enter.

## Listening screen

After the scene loads, a dedicated listening screen replaces the old click-to-begin card. It uses a charcoal green background, a fine headphone illustration, a serif “Listen closely.” heading and a visible Enter key. The copy explains that directional sound helps locate things in the darkness. Enter starts the scene from anywhere on the screen; the focused button also supports pointer activation. Clicking the background does not start play.

Audio unlock and pointer capture run synchronously inside the activation gesture. Repeated, composing and modified Enter presses do not start play, and activation is guarded during the 650 ms departure fade. The listener is removed and focus returns to the canvas before the scene continues. Reduced-motion preferences skip the departure delay. Entry styling is removed before ordinary story cards are displayed.

`/tests/browser/entry.html` previews the real screen without touching saves or loading the game. Press Enter to verify activation, audio unlock, focus restoration, listener removal and ordinary story-card styling; pointer capture is reported separately because embedded browsers may reject it. Preview again repeats the check.

## Living atmosphere

Two translucent rain layers fall through the open doorway, clipped to the exterior. A low-opacity glow and flame highlight flicker independently over the lamp. Both effects track the image's cover crop. Reduced-motion preferences hide moving rain and hold the lamplight steady. Hidden tabs pause the visual loops.

The welcome screen synthesizes stereo rain, a quiet low beating drone, and slowly modulated wind using Web Audio. Audio is created only after a player gesture, respects the shared sound setting, and has a visible ambience toggle in the footer. Hidden tabs are muted. Starting or continuing fades out every source and closes the menu audio context, so the soundscape cannot continue under gameplay. No external sound files or downloads are required.

## Final background prompt

Use case: historical-scene. Final production background artwork for a full-screen horror game main menu, 16:9 wide landscape. Game: The Unbroken Debt, 1932 rural Cambodia. Cinematic grounded Southeast Asian psychological survival horror. View from within a decaying dark teak house toward a distant open doorway on RIGHT HALF, old wooden plank floor, woven bamboo walls, humid mist, monsoon streaks beyond doorway, pale desaturated green-grey moonlight barely revealing depth. A length of plain faded red binding thread draped from a foreground beam on the extreme right, with a small exhausted kerosene lamp below casting a faint rusty glow. Dread and claustrophobia. Deep green-black shadows, dirty bone-white highlights, extremely restrained oxblood red, dusty photographic grain, realistic materials, moody high-end game environment key art. LEFT HALF almost black with only faint wall texture, ample negative space for menu and logo added separately. Right half doorway, depth and objects clearly readable but dark. No modern electric fittings, no Thai lettering or symbols, no sacred iconography, no people, no ghosts, no monsters. NO TEXT, NO LOGO, NO UI, NO WATERMARK. Original composition.

## Final logo prompt

Use case: logo-brand. Create a final isolated transparent-background game title wordmark for THE UNBROKEN DEBT, original Southeast Asian psychological survival horror identity. Exact text only: small 'THE' above a large condensed 'UNBROKEN' and large 'DEBT' underneath. Centered compact stacked title lockup, wider than tall. Highly readable tall narrow sharp serif lettering with subtly irregular hand-cut edges, aged bone-white pigment, light scratched and chipped screenprint texture. DEBT in muted dried oxblood red #8e302c, other letters bone-white #e5dfd2. A single fine red thread extends horizontally underneath and curls back into a tight binding knot at center, minimal abstract and secular, no religious characters. The negative spaces of letters remain transparent. Atmospheric terrifying elegant restrained horror title, professional AAA game logo finish, excellent at menu size, no excessive drips, no fake alphabet, no Thai motifs, no skulls, no symbol above title, no glow, no shadows, no surrounding background, no other text. Truly transparent background.

