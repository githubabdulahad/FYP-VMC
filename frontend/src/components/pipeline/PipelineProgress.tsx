import clsx from 'clsx';
import { motion } from 'framer-motion';
import { Check } from 'lucide-react';
import { PIPELINE_STAGES } from '@/utils/pipeline';
import type { PipelineStage } from '@/types';

interface PipelineProgressProps {
  activeStage: PipelineStage;
  failed?: boolean;
}

export function PipelineProgress({ activeStage, failed }: PipelineProgressProps) {
  const activeIndex = PIPELINE_STAGES.findIndex((s) => s.id === activeStage);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 overflow-x-auto pb-2">
        {PIPELINE_STAGES.map((stage, index) => {
          const done = index < activeIndex;
          const active = index === activeIndex;
          const isFailed = failed && active;

          return (
            <div key={stage.id} className="flex min-w-[72px] flex-1 flex-col items-center gap-2">
              <motion.div
                className={clsx(
                  'flex h-9 w-9 items-center justify-center rounded-full border text-xs font-bold transition-colors',
                  done && 'border-teal-500/50 bg-teal-500/20 text-teal-300',
                  active && !isFailed && 'border-purple-400 bg-purple-500/25 text-purple-200 shadow-lg shadow-purple-500/20',
                  active && isFailed && 'border-rose-400 bg-rose-500/25 text-rose-200',
                  !done && !active && 'border-slate-600/40 bg-surface-800 text-slate-500',
                )}
                animate={active && !isFailed ? { scale: [1, 1.08, 1] } : {}}
                transition={{ repeat: Infinity, duration: 1.6 }}
              >
                {done ? <Check className="h-4 w-4" /> : index + 1}
              </motion.div>
              <span
                className={clsx(
                  'text-center text-[10px] font-medium leading-tight',
                  active ? 'text-white' : 'text-slate-500',
                )}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>
      {activeIndex >= 0 && (
        <p className="text-center text-sm text-slate-400">
          {failed ? 'Processing failed' : PIPELINE_STAGES[activeIndex]?.description}
        </p>
      )}
    </div>
  );
}
