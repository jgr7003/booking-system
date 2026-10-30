# Prompt para generar imágenes de fondo del inicio de sesión

**Cómo usarlo:** copiar el bloque de abajo en el generador de imágenes (Midjourney, DALL·E, Imagen, Firefly, etc.). Pedir una imagen por cada **escena** de la lista, con el mismo bloque de estilo, para que la serie se vea coherente. Las imágenes van detrás de la tarjeta de login de la pantalla «Inicio de sesión» (ver [claude-design-usuarios.md](claude-design-usuarios.md), tablero 1).

Formatos a pedir para cada escena:

| Uso | Proporción | Tamaño sugerido |
|---|---|---|
| Desktop | 16:9 | 2560 × 1440 |
| Mobile | 9:16 | 1170 × 2532 |

---

## Prompt (en inglés, porque la mayoría de los generadores responden mejor)

```
Background image for the sign-in screen of a corporate travel booking platform.

Concept: business travel made calm and organized. Companies book flights for their people;
the platform is reliable, precise and quiet, not flashy. The image should feel like the calm
moment before a trip: anticipation, order, wide open space.

Scene: {SCENE}

Style:
- Photographic, natural light, soft and slightly desaturated, editorial look, high detail.
- Plenty of empty, low-detail space: a sign-in card (about 440 px wide) sits over the
  {CARD_SIDE} of the image, so that area must be calm (sky, soft gradient, blurred background),
  with no faces, text or busy details behind it.
- Color palette: deep blue (#1D4ED8, #1E3A8A) and cool grays (#111827, #4B5563, #F3F4F6) as
  the dominant tones, with at most a small warm accent (early morning light). No saturated
  orange, red or purple.
- Should still read well with a dark overlay at 40% opacity on top.

Avoid: any text, letters, numbers, logos, airline liveries or brand marks; recognizable
airports or landmarks; identifiable faces looking at the camera; people in the card area;
stock-photo clichés (handshakes, people pointing at laptops, suitcases full of clothes);
cartoon or 3D-render look; lens flares; watermarks.
```

Reemplazar `{CARD_SIDE}` por `center` (desktop centrado) o `lower half` (mobile).

## Escenas (`{SCENE}`)

1. **Cielo desde la ventanilla:** "View through an airplane window at dawn, above a calm sea of clouds, the wing barely visible at the edge; most of the frame is soft sky."
2. **Terminal vacía al amanecer:** "A modern, empty airport terminal at sunrise seen from a distance, large glass facade, long soft shadows on a polished floor, out-of-focus aircraft tail beyond the glass; no signage readable."
3. **Viajero de espaldas:** "A business traveler seen from behind and far away, small in the frame, walking with a carry-on along a bright, minimal concourse toward large windows; blurred, anonymous."
4. **Avión despegando a lo lejos:** "A small silhouette of a passenger jet climbing in the distance over a quiet city at blue hour, wide sky occupying two thirds of the image."
5. **Abstracta (alternativa sin fotografía):** "Abstract, minimal composition of thin flight paths drawn as soft curved lines across a deep blue gradient, faint dotted arcs connecting distant points, like a calm route map seen from far away; no geography labels."

## Para elegir

- Probar las imágenes debajo de la tarjeta real, con el overlay, en desktop (1280 px) y mobile (390 px).
- Para las instalaciones de empresas, la misma serie sirve. Cuando exista la marca por empresa (pendiente de la etapa 3, §19), cada empresa podrá subir la suya.
- Guardar las elegidas en `frontend/src/assets/login/` como `.webp` (calidad ~80) y anotar la fuente y la licencia de cada una.
