import { useSelector } from 'react-redux';
import { RootState } from '../store';

export const useSelectedPortfolio = () => {
  return useSelector((state: RootState) => state.portfolio.selectedPortfolioId);
};

// Made with Bob
