import { motion, useReducedMotion } from "framer-motion";

export type DociState = "idle" | "greeting" | "focus-email" | "focus-password" | "success" | "concerned" | "thinking" | "processing" | "evidence" | "insufficient" | "empty" | "comparing";
const LABEL: Record<DociState, string> = {
  idle: "Doci is waiting", greeting: "Doci is greeting you", "focus-email": "Doci is looking at the email field", "focus-password": "Doci is looking away to respect your privacy",
  success: "Doci is happy", concerned: "Doci looks concerned", thinking: "Doci is thinking", processing: "Doci is reading your document", evidence: "Doci found evidence",
  insufficient: "Doci could not find enough evidence", empty: "Doci is waiting for your first document", comparing: "Doci is comparing candidates",
};

export default function Doci({ state = "idle", size = 96 }: { state?: DociState; size?: number }) {
  const reduce = useReducedMotion();
  const happy = state === "success" || state === "greeting" || state === "evidence";
  const worried = state === "concerned" || state === "insufficient";
  const shy = state === "focus-password";
  const look = state === "focus-email" ? { x: -2, y: -1 } : state === "thinking" || state === "processing" ? { x: 2, y: -2 } : { x: 0, y: 0 };
  const bob = reduce ? {} : state === "processing" || state === "thinking" ? { rotate: [-2, 2, -2] } : state === "success" ? { y: [0, -6, 0] } : { y: [0, -3, 0] };
  return (
    <motion.svg role="img" aria-label={LABEL[state]} width={size} height={size * 1.15} viewBox="0 0 100 115" data-state={state}
      animate={bob} transition={{ repeat: reduce ? 0 : Infinity, duration: state === "processing" ? 0.9 : 2.6, ease: "easeInOut" }}>
      <path d="M14 8h50l28 28v68a5 5 0 0 1-5 5H14a5 5 0 0 1-5-5V13a5 5 0 0 1 5-5z" fill="var(--teal)" />
      <path d="M64 8v23a5 5 0 0 0 5 5h23z" fill="var(--teal-dark)" />
      <rect x="18" y="42" width="64" height="55" rx="8" fill="#fffdf9" />
      {shy ? (<g stroke="#0f3d3a" strokeWidth="3" strokeLinecap="round"><path d="M32 62q6 4 12 0" fill="none" /><path d="M56 62q6 4 12 0" fill="none" /></g>) : (
        <g fill="#0f3d3a"><circle cx={38 + look.x} cy={62 + look.y} r="5" /><circle cx={62 + look.x} cy={62 + look.y} r="5" />
          <circle cx={39.5 + look.x} cy={60.5 + look.y} r="1.6" fill="#fff" /><circle cx={63.5 + look.x} cy={60.5 + look.y} r="1.6" fill="#fff" /></g>)}
      {worried && <g stroke="#0f3d3a" strokeWidth="2.5" strokeLinecap="round"><path d="M30 50l14 3" /><path d="M70 50l-14 3" /></g>}
      <path d={happy ? "M40 76q10 11 20 0" : worried ? "M42 82q8-7 16 0" : "M43 78h14"} stroke="#0f3d3a" strokeWidth="3" fill="none" strokeLinecap="round" />
      {state === "processing" && <g fill="var(--teal)"><rect x="24" y="90" width="52" height="3" rx="1.5" opacity=".5" /></g>}
    </motion.svg>
  );
}
