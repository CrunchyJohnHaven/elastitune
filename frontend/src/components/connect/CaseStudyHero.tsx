import React from 'react';
import { motion } from 'framer-motion';

/**
 * Case study hero: shows the Elastic product store before/after code snippets
 * and the 94% improvement headline. Replaces the generic preview stats.
 */
export default function CaseStudyHero() {
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        zIndex: 20,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: '40px 48px',
        pointerEvents: 'none',
        overflow: 'hidden',
      }}
    >
      {/* Headline */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.6 }}
      >
        <div
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 10,
            color: 'rgba(77,163,255,0.7)',
            letterSpacing: '0.14em',
            textTransform: 'uppercase',
            marginBottom: 8,
          }}
        >
          Real-world result
        </div>
        <h2
          style={{
            fontFamily: 'Inter, sans-serif',
            fontWeight: 700,
            fontSize: 28,
            color: '#EEF3FF',
            margin: '0 0 6px',
            lineHeight: 1.2,
            letterSpacing: '-0.01em',
          }}
        >
          <span style={{ color: '#4ADE80' }}>94%</span> improvement
        </h2>
        <p
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: 13,
            color: '#9AA4B2',
            margin: '0 0 24px',
            lineHeight: 1.5,
            maxWidth: 440,
          }}
        >
          on Elastic's own product search demo.
          <br />
          Same index. Same 931 documents. 3 lines of config.
        </p>
      </motion.div>

      {/* Before / After code blocks */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.5 }}
        style={{
          display: 'flex',
          gap: 16,
          marginBottom: 24,
          flexWrap: 'wrap',
        }}
      >
        {/* Before */}
        <div
          style={{
            flex: '1 1 200px',
            maxWidth: 280,
            background: 'rgba(251,113,133,0.06)',
            border: '1px solid rgba(251,113,133,0.15)',
            borderRadius: 10,
            padding: '14px 16px',
          }}
        >
          <div
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 10,
              color: '#FB7185',
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              marginBottom: 10,
            }}
          >
            Before — nDCG 0.492
          </div>
          <pre
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 11,
              color: 'rgba(238,243,255,0.8)',
              margin: 0,
              lineHeight: 1.6,
              whiteSpace: 'pre-wrap',
            }}
          >
{`"fields": [
  "name",
  "category",
  "description"
]`}
          </pre>
          <p
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 10,
              color: 'rgba(154,164,178,0.5)',
              margin: '8px 0 0',
              lineHeight: 1.4,
            }}
          >
            Equal weight, no match type, no MSM
          </p>
        </div>

        {/* After */}
        <div
          style={{
            flex: '1 1 200px',
            maxWidth: 280,
            background: 'rgba(74,222,128,0.06)',
            border: '1px solid rgba(74,222,128,0.15)',
            borderRadius: 10,
            padding: '14px 16px',
          }}
        >
          <div
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 10,
              color: '#4ADE80',
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              marginBottom: 10,
            }}
          >
            After — nDCG 0.956
          </div>
          <pre
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 11,
              color: 'rgba(238,243,255,0.9)',
              margin: 0,
              lineHeight: 1.6,
              whiteSpace: 'pre-wrap',
            }}
          >
{`"fields": [
  "name^5.0",
  "description^3.0",
  "brand^0.8"
],
"type": "cross_fields",
"minimum_should_match": "75%"`}
          </pre>
          <p
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 10,
              color: 'rgba(154,164,178,0.5)',
              margin: '8px 0 0',
              lineHeight: 1.4,
            }}
          >
            Tuned weights, cross_fields, 75% MSM
          </p>
        </div>
      </motion.div>

      {/* Context line */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6, duration: 0.5 }}
        style={{
          display: 'flex',
          gap: 20,
          alignItems: 'center',
          flexWrap: 'wrap',
        }}
      >
        <Stat value="13,114" label="experiments run" />
        <Stat value="931" label="products indexed" />
        <Stat value="8" label="test queries" />
        <Stat value="1 night" label="wall-clock time" />
      </motion.div>

      {/* Source */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.75, duration: 0.4 }}
        style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: 11,
          color: 'rgba(107,116,128,0.6)',
          margin: '20px 0 0',
          lineHeight: 1.5,
          maxWidth: 460,
        }}
      >
        Source: Elastic's own{' '}
        <span style={{ color: 'rgba(77,163,255,0.6)' }}>
          elasticsearch-labs/hybrid-search-for-an-e-commerce-product-catalogue
        </span>
        {' '}demo app. The original search query is at line 33 of{' '}
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10 }}>api.py</span>.
        Not misconfigured. Just never optimized.
      </motion.p>
    </div>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <div
        style={{
          fontFamily: 'Inter, sans-serif',
          fontWeight: 700,
          fontSize: 16,
          color: '#EEF3FF',
          lineHeight: 1,
        }}
      >
        {value}
      </div>
      <div
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 10,
          color: 'rgba(154,164,178,0.5)',
          marginTop: 2,
        }}
      >
        {label}
      </div>
    </div>
  );
}
