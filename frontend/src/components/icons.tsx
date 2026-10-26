import type { SVGProps } from "react";

/** Icons drawn exactly as in the design (docs/frontend, proposal A). */
type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function Stroke({ size = 16, strokeWidth = 2, children, ...props }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      {...props}
    >
      {children}
    </svg>
  );
}

/** Brand mark of "Vuelos". */
export const LogoIcon = (p: IconProps) => (
  <Stroke size={22} {...p}>
    <path d="M2 16l20-6-20-6 4 6-4 6z" />
  </Stroke>
);

export const SwapIcon = (p: IconProps) => (
  <Stroke size={14} {...p}>
    <path d="M4 8h16l-4-4M20 16H4l4 4" />
  </Stroke>
);

export const CalendarIcon = (p: IconProps) => (
  <Stroke size={14} {...p}>
    <rect x="4" y="5" width="16" height="15" rx="2" />
    <path d="M4 10h16M9 3v4M15 3v4" />
  </Stroke>
);

export const PersonIcon = ({ size = 14, ...p }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden {...p}>
    <circle cx="12" cy="8" r="4" />
    <path d="M4 21a8 8 0 0 1 16 0z" />
  </svg>
);

export const PencilIcon = (p: IconProps) => (
  <Stroke size={14} {...p}>
    <path d="M4 20h4L19 9l-4-4L4 16z" />
  </Stroke>
);

/** Departing plane above a runway, before the results title. */
export const DepartureIcon = (p: IconProps) => (
  <Stroke size={22} {...p}>
    <path d="M3 20h18M5 15l14-5-1.5-2.5-4.5 1.5-5-4-2 .8 3 4.6-4 1.4-2-1.5-1.5.6z" />
  </Stroke>
);

export const ClockIcon = (p: IconProps) => (
  <Stroke size={16} strokeWidth={2.2} {...p}>
    <circle cx="12" cy="13" r="8" />
    <path d="M12 9v4l2 2M9 2h6" />
  </Stroke>
);

/** Plane in flight, centered on the line of a direct flight. */
export const PlaneIcon = ({ size = 20, ...p }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden {...p}>
    <path
      d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z"
      transform="rotate(90 12 12)"
    />
  </svg>
);

export const CarryOnIcon = (p: IconProps) => (
  <Stroke size={15} {...p}>
    <rect x="7" y="8" width="10" height="12" rx="2" />
    <path d="M10 8V5h4v3" />
  </Stroke>
);

export const CheckedBagIcon = (p: IconProps) => (
  <Stroke size={15} {...p}>
    <rect x="5" y="7" width="14" height="13" rx="2" />
    <path d="M9 7V4h6v3M9 20v1M15 20v1" />
  </Stroke>
);

export const CityIcon = (p: IconProps) => (
  <Stroke size={18} {...p}>
    <path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6" />
  </Stroke>
);

export const TrashIcon = (p: IconProps) => (
  <Stroke size={15} {...p}>
    <path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13" />
  </Stroke>
);

export const HotelIcon = (p: IconProps) => (
  <Stroke size={18} {...p}>
    <path d="M3 20V9l9-5 9 5v11M3 20h18M9 20v-5h6v5M8 11h.01M12 11h.01M16 11h.01" />
  </Stroke>
);

export const AlertIcon = (p: IconProps) => (
  <Stroke size={20} {...p}>
    <path d="M12 9v4M12 17h.01" />
    <path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
  </Stroke>
);

export const SpinnerIcon = (p: IconProps) => (
  <Stroke size={20} {...p}>
    <path d="M21 12a9 9 0 1 1-9-9" />
  </Stroke>
);
