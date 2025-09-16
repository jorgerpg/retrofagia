import { Star } from "lucide-react";

export default function Stars({
  value = 0,
  onChange,
  size = 22,
  readOnly = false,
}: {
  value?: number;
  onChange?: (v: number) => void;
  size?: number;
  readOnly?: boolean;
}) {
  const stars = [1, 2, 3, 4, 5];
  return (
    <div className="inline-flex items-center gap-1">
      {stars.map((n) => {
        const active = value >= n;
        return (
          <button
            key={n}
            type="button"
            disabled={readOnly}
            onClick={() => onChange?.(n)}
            className={readOnly ? "cursor-default" : "hover:scale-105 transition"}
            title={`${n} estrela${n>1?"s":""}`}
          >
            <Star size={size} className={active ? "text-yellow-300" : "text-white/30"} fill={active ? "currentColor" : "none"} />
          </button>
        );
      })}
    </div>
  );
}
