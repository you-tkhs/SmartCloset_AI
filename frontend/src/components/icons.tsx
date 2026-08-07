interface IconProps {
  className?: string;
}

const commonProps = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export function ClosetIcon({ className }: IconProps) {
  return (
    <svg {...commonProps} className={className} aria-hidden="true">
      <circle cx="12" cy="5" r="1.5" />
      <path d="M12 6.5v2" />
      <path d="M4 20l7-6a2 2 0 0 1 2 0l7 6" />
      <path d="M2 20h20" />
    </svg>
  );
}

export function UploadIcon({ className }: IconProps) {
  return (
    <svg {...commonProps} className={className} aria-hidden="true">
      <path d="M12 16V4" />
      <path d="M7 9l5-5 5 5" />
      <path d="M4 20h16" />
    </svg>
  );
}

export function SparklesIcon({ className }: IconProps) {
  return (
    <svg {...commonProps} className={className} aria-hidden="true">
      <path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3z" />
      <path d="M19 15l.7 2.1L22 18l-2.3.9L19 21l-.7-2.1L16 18l2.3-.9L19 15z" />
    </svg>
  );
}
