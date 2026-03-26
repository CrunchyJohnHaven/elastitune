import type { EvalCase } from '@/types/contracts';

export const TMDB_MOVIES_EVAL_SET: EvalCase[] = [
  { id: 'tmdb_eval_space', query: 'space adventure sci-fi', relevantDocIds: ['6795', '316784', '5551', '10690'], difficulty: 'easy' },
  { id: 'tmdb_eval_romcom', query: 'romantic comedy new york city', relevantDocIds: ['22597', '31016', '10641', '12637'], difficulty: 'medium' },
  { id: 'tmdb_eval_spy', query: 'spy thriller cia conspiracy', relevantDocIds: ['20662', '56292', '39514', '10764'], difficulty: 'medium' },
  { id: 'tmdb_eval_superhero', query: 'superhero team saves world', relevantDocIds: ['24428', '99861', '299536', '284054'], difficulty: 'easy' },
  { id: 'tmdb_eval_animation', query: 'animated family adventure talking animals', relevantDocIds: ['8587', '9502', '11544', '585'], difficulty: 'easy' },
  { id: 'tmdb_eval_horror', query: 'haunted house supernatural horror', relevantDocIds: ['694', '138843', '1933', '346364'], difficulty: 'medium' },
  { id: 'tmdb_eval_heist', query: 'bank robbery heist crew', relevantDocIds: ['9737', '500', '111', '2069'], difficulty: 'medium' },
  { id: 'tmdb_eval_time', query: 'time travel paradox future', relevantDocIds: ['105', '264660', '329865', '11'], difficulty: 'hard' },
  { id: 'tmdb_eval_war', query: 'world war ii battlefield drama', relevantDocIds: ['857', '424', '423', '935'], difficulty: 'medium' },
  { id: 'tmdb_eval_detective', query: 'detective serial killer mystery', relevantDocIds: ['807', '274', '1422', '157336'], difficulty: 'hard' },
  { id: 'tmdb_eval_fantasy', query: 'fantasy quest magical kingdom', relevantDocIds: ['121', '122', '123', '12445'], difficulty: 'easy' },
  { id: 'tmdb_eval_music', query: 'music fame performance drama', relevantDocIds: ['10376', '332562', '889', '244786'], difficulty: 'medium' },
];
