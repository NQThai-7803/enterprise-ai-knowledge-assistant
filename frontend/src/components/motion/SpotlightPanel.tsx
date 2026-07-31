import type { CSSProperties, HTMLAttributes } from "react";
import { useState } from "react";
import { clsx } from "clsx";

export function SpotlightPanel({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  const [style, setStyle] = useState<CSSProperties>({});

  return (
    <div
      className={clsx("spotlight-panel rounded-token", className)}
      style={style}
      onPointerMove={(event) => {
        const rect = event.currentTarget.getBoundingClientRect();
        setStyle({
          "--spotlight-x": `${event.clientX - rect.left}px`,
          "--spotlight-y": `${event.clientY - rect.top}px`,
          "--spotlight-opacity": "1",
        } as CSSProperties);
      }}
      onPointerLeave={() => setStyle({ "--spotlight-opacity": "0" } as CSSProperties)}
      {...props}
    >
      {children}
    </div>
  );
}