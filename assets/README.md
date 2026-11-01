# Profile artwork

The four hero SVGs adapt the visual identity of [hridya.tech](https://hridya.tech):
Manrope, Caveat, the orange 5×7 dot-matrix display, and the aluminium tray.
The lettering uses vector outlines, so it does not require installed fonts or external font requests.

`hero-light.svg` is the default. The profile's `<picture>` selects a dark version
and a separate composition for screens up to 600 pixels wide.
All four files are static, self-contained SVGs with titles and descriptions.

Source artwork and typefaces come from Hridya's portfolio. The display glyphs match
`src/components/portfolio/dot-matrix-font.ts` in that project.
Manrope, Caveat, and IBM Plex Mono use the SIL Open Font License.
The SVGs contain outlines only, with no embedded font software.
