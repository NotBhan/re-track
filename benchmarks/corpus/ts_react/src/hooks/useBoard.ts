import { useContext } from 'react';
import { BoardContext, BoardContextValue } from '../context/BoardContext';

export function useBoard(): BoardContextValue {
  const context = useContext(BoardContext);
  if (!context) {
    throw new Error('useBoard must be used within a BoardProvider');
  }
  return context;
}
