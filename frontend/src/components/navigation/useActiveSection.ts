import { useLocation } from 'react-router-dom';
import { RailSection } from './navigationData';

/**
 * Maps the current route pathname to the active rail section key.
 * Returns null if no section matches (e.g. login page).
 */
export function useActiveSection(sections: RailSection[]): string | null {
  const { pathname } = useLocation();

  for (const section of sections) {
    if (section.path && section.path === pathname) return section.key;
    if (section.items?.some((item) => item.path === pathname)) return section.key;
    if (section.assetGroups?.some((g) => g.items.some((i) => i.path === pathname)))
      return section.key;
    if (section.bottomItems?.some((item) => item.path === pathname)) return section.key;
  }

  return null;
}
