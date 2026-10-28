/** A value as the design shows it: its text and the color that tells whether it is good news. */
export type Tone = "ok" | "warn" | "bad" | "na";

export interface Cell {
  label: string;
  tone: Tone;
}
