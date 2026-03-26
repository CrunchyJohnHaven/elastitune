import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useWalkthroughStore, WALKTHROUGH_STEPS } from '@/store/useWalkthroughStore';

/**
 * Floating overlay that shows step-by-step explanations during a guided demo.
 * Renders on top of the RunScreen / ReportScreen.
 */
export default function WalkthroughOverlay() {
  const { active, currentStep, nextStep, prevStep, stopWalkthrough } =
    useWalkthroughStore();

  if (!active) return null;

  const step = WALKTHROUGH_STEPS[currentStep];
  if (!step) return null;

  const isFirst = currentStep === 0;
  const isLast = currentStep === WALKTHROUGH_STEPS.length - 1;
  const progress = ((currentStep + 1) / WALKTHROUGH_STEPS.length) * 100;

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={step.id}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.3 }}
        style={{
          position: 'fixed',
          bottom: 32,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 9999,
          width: 520,
          maxWidth: 'calc(100vw - 64px)',
        }}
      >
        <div
          style={{
            background: 'rgba(5, 7, 11, 0.94)',
            border: '1px solid rgba(77, 163, 255, 0.25)',
            borderRadius: 16,
            padding: '24px 28px 20px',
            backdropFilter: 'blur(20px)',
            boxShadow:
              '0 32px 80px rgba(0, 0, 0, 0.5), 0 0 1px rgba(77, 163, 255, 0.3)',
          }}
        >
          {/* Progress bar */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 16,
              right: 16,
              height: 3,
              borderRadius: '0 0 3px 3px',
              background: 'rgba(255, 255, 255, 0.06)',
              overflow: 'hidden',
            }}
          >
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
              style={{
                height: '100%',
                background: 'linear-gradient(90deg, #4DA3FF, #7CE7FF)',
                borderRadius: 3,
              }}
            />
          </div>

          {/* Step counter */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: 12,
            }}
          >
            <div
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 11,
                color: '#4DA3FF',
                letterSpacing: '0.06em',
              }}
            >
              Step {currentStep + 1} of {WALKTHROUGH_STEPS.length}
            </div>

            {/* Close button */}
            <button
              onClick={stopWalkthrough}
              aria-label="Exit walkthrough"
              style={{
                background: 'none',
                border: 'none',
                color: 'rgba(154, 164, 178, 0.6)',
                cursor: 'pointer',
                fontSize: 16,
                padding: '2px 6px',
                lineHeight: 1,
              }}
              title="Exit walkthrough"
              >
                ✕
              </button>
            </div>

          {/* Title */}
          <motion.h3
            key={`title-${step.id}`}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
            style={{
              fontFamily: 'Inter, sans-serif',
              fontWeight: 700,
              fontSize: 18,
              color: '#EEF3FF',
              margin: '0 0 8px',
              lineHeight: 1.3,
            }}
          >
            {step.title}
          </motion.h3>

          {/* Description */}
          <motion.p
            key={`desc-${step.id}`}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.15 }}
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 14,
              color: '#C5CDD8',
              lineHeight: 1.65,
              margin: '0 0 20px',
            }}
          >
            {step.description}
          </motion.p>

          {/* Navigation buttons */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 12,
            }}
          >
            <button
              onClick={prevStep}
              disabled={isFirst}
              aria-label="Previous walkthrough step"
              style={{
                fontFamily: 'Inter, sans-serif',
                fontSize: 13,
                fontWeight: 500,
                color: isFirst ? 'rgba(154, 164, 178, 0.3)' : '#9AA4B2',
                background: 'none',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: 8,
                padding: '8px 16px',
                cursor: isFirst ? 'default' : 'pointer',
                transition: 'color 0.2s',
              }}
              >
              Back
            </button>

            <button
              onClick={stopWalkthrough}
              aria-label="Skip walkthrough"
              style={{
                fontFamily: 'Inter, sans-serif',
                fontSize: 13,
                fontWeight: 500,
                color: '#9AA4B2',
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: 8,
                padding: '8px 14px',
                cursor: 'pointer',
                transition: 'color 0.2s, background 0.2s',
              }}
            >
              Skip Tour
            </button>

            <div
              style={{
                display: 'flex',
                gap: 4,
              }}
            >
              {WALKTHROUGH_STEPS.map((_, i) => (
                <div
                  key={i}
                  style={{
                    width: i === currentStep ? 16 : 6,
                    height: 6,
                    borderRadius: 3,
                    background:
                      i === currentStep
                        ? '#4DA3FF'
                        : i < currentStep
                          ? 'rgba(77, 163, 255, 0.3)'
                          : 'rgba(255, 255, 255, 0.1)',
                    transition: 'all 0.3s',
                  }}
                />
              ))}
            </div>

            {isLast ? (
              <button
                onClick={stopWalkthrough}
                aria-label="Finish walkthrough"
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 13,
                  fontWeight: 600,
                  color: '#05070B',
                  background: 'linear-gradient(135deg, #4DA3FF, #7CE7FF)',
                  border: 'none',
                  borderRadius: 8,
                  padding: '8px 20px',
                  cursor: 'pointer',
                }}
              >
                Finish Tour
              </button>
            ) : (
              <button
                onClick={nextStep}
                aria-label="Next walkthrough step"
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 13,
                  fontWeight: 600,
                  color: '#05070B',
                  background: 'linear-gradient(135deg, #4DA3FF, #7CE7FF)',
                  border: 'none',
                  borderRadius: 8,
                  padding: '8px 20px',
                  cursor: 'pointer',
                }}
              >
                Next
              </button>
            )}
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
