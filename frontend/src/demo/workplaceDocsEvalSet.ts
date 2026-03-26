import type { EvalCase } from '@/types/contracts';

export const WORKPLACE_DOCS_EVAL_SET: EvalCase[] = [
  { id: "wp_eval_001", query: "how many days can I work from home", relevantDocIds: ["1", "2", "3"], difficulty: "medium", personaHint: "remote employee" },
  { id: "wp_eval_002", query: "what happens to my PTO when I quit", relevantDocIds: ["5"], difficulty: "hard", personaHint: "departing employee" },
  { id: "wp_eval_003", query: "who owns the code I write on weekends", relevantDocIds: ["8"], difficulty: "hard", personaHint: "software engineer" },
  { id: "wp_eval_004", query: "can I bring my dog to the office", relevantDocIds: ["10"], difficulty: "medium", personaHint: "office worker" },
  { id: "wp_eval_005", query: "how do I get promoted to senior engineer", relevantDocIds: ["6", "11"], difficulty: "hard", personaHint: "software engineer" },
  { id: "wp_eval_006", query: "what are our revenue targets this year", relevantDocIds: ["4", "12"], difficulty: "hard", personaHint: "sales manager" },
  { id: "wp_eval_007", query: "report harassment or bullying at work", relevantDocIds: ["9"], difficulty: "hard", personaHint: "concerned employee" },
  { id: "wp_eval_008", query: "first week checklist new job", relevantDocIds: ["15"], difficulty: "medium", personaHint: "new hire" },
  { id: "wp_eval_009", query: "how does the company decide my pay raise", relevantDocIds: ["13", "11"], difficulty: "hard", personaHint: "engineering manager" },
  { id: "wp_eval_010", query: "tips for working with sales as an engineer", relevantDocIds: ["7"], difficulty: "medium", personaHint: "software engineer" },
  { id: "wp_eval_011", query: "update my W4 tax withholding", relevantDocIds: ["14"], difficulty: "medium", personaHint: "HR assistant" },
  { id: "wp_eval_012", query: "mandatory return to office schedule", relevantDocIds: ["2", "3"], difficulty: "hard", personaHint: "remote employee" },
  { id: "wp_eval_013", query: "side project intellectual property rules", relevantDocIds: ["8"], difficulty: "hard", personaHint: "software engineer" },
  { id: "wp_eval_014", query: "customer retention goals FY24", relevantDocIds: ["4"], difficulty: "hard", personaHint: "account executive" },
  { id: "wp_eval_015", query: "ergonomic home office setup requirements", relevantDocIds: ["1"], difficulty: "hard", personaHint: "remote employee" },
  { id: "wp_eval_016", query: "what is the company policy on data security and passwords", relevantDocIds: ["9", "1"], difficulty: "hard", personaHint: "IT admin" },
];
