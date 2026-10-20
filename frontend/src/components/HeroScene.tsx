import { useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import Doci from "./Doci";
const CAPTIONS = ["A document arrives", "Doci opens it", "Pages are split into searchable passages", "Evidence links connect answers to sources", "Findings become comparisons"];
export default function HeroScene() {
  const reduce = useReducedMotion(); const [step, setStep] = useState(reduce ? 4 : 0); const [skip, setSkip] = useState(false);
  useEffect(() => { if (reduce || skip || step >= 4) return; const t = setTimeout(() => setStep(step + 1), 1600); return () => clearTimeout(t); }, [step, reduce, skip]);
  const final = skip ? 4 : step;
  return (
    <div className="hero-scene glass" aria-label="Illustration of how DocuMind AI works (sample illustration, not real data)">
      <div className="scene-stage">
        <AnimatePresence mode="wait">
          <motion.div key={final} initial={{ opacity: 0, y: reduce ? 0 : 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: reduce ? 0 : 0.4 }} className="scene-inner">
            {final <= 1 && <Doci state={final === 0 ? "greeting" : "processing"} size={120} />}
            {final === 2 && <div className="chunks">{[1, 2, 3].map((n) => <motion.div key={n} className="chunk" initial={{ x: -20 * n }} animate={{ x: 0 }}>Passage {n} · p.{n}</motion.div>)}</div>}
            {final === 3 && <div className="chunks"><div className="chunk hl">“…accuracy reached 92.5%…” · p.4</div><div className="link-line" /><div className="chunk">Answer [1]</div></div>}
            {final === 4 && <div className="chunks"><div className="chunk">Paper A: 92.5%</div><div className="chunk">Paper B: 71.0%</div><div className="chunk warn">Possible conflict: needs review</div></div>}
          </motion.div>
        </AnimatePresence>
      </div>
      <p className="muted center" aria-live="polite">{CAPTIONS[final]}</p>
      {final < 4 && <button className="btn ghost small" onClick={() => setSkip(true)}>Skip animation</button>}
    </div>
  );
}
