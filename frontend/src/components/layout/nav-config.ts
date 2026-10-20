import {
  Activity,
  BarChart3,
  Boxes,
  CalendarClock,
  FileCode2,
  FileSearch,
  GitBranch,
  GitCompare,
  GitPullRequest,
  History,
  LayoutDashboard,
  type LucideIcon,
  Network,
  Radar,
  Rocket,
  ShieldCheck,
  Sparkles,
  Target,
  Waypoints,
} from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  needsRepository?: boolean;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { to: "/", label: "Dashboard", icon: LayoutDashboard },
      { to: "/executive", label: "Executive Summary", icon: BarChart3 },
    ],
  },
  {
    label: "Repositories",
    items: [
      { to: "/repositories", label: "Repository Explorer", icon: GitBranch },
      { to: "/git", label: "Git Analysis", icon: History, needsRepository: true },
      { to: "/branches", label: "Branch Comparison", icon: GitCompare, needsRepository: true },
      { to: "/pull-requests", label: "Pull Request Analysis", icon: GitPullRequest, needsRepository: true },
      { to: "/dependency-map", label: "Repository Dependency Map", icon: Network },
    ],
  },
  {
    label: "Analysis",
    items: [
      { to: "/ast", label: "AST Analysis", icon: FileCode2, needsRepository: true },
      { to: "/dependencies", label: "Dependency Analysis", icon: Boxes, needsRepository: true },
      { to: "/security", label: "Security Analysis", icon: ShieldCheck, needsRepository: true },
      { to: "/impact", label: "Impact Analysis", icon: Target, needsRepository: true },
      { to: "/similarity", label: "Historical Similarity", icon: Waypoints },
      { to: "/criticality", label: "Criticality Assessment", icon: Radar, needsRepository: true },
      { to: "/story", label: "AI Story Report", icon: Sparkles, needsRepository: true },
    ],
  },
  {
    label: "Delivery",
    items: [
      { to: "/pre-commit", label: "Pre Commit Validation", icon: FileSearch, needsRepository: true },
      { to: "/release", label: "Release Readiness", icon: Rocket, needsRepository: true },
    ],
  },
  {
    label: "Operations",
    items: [
      { to: "/monitoring", label: "Workspace Monitoring", icon: Activity },
      { to: "/events", label: "Change Events", icon: CalendarClock },
    ],
  },
];

/** Every route in the application, in navigation order. */
export const ALL_NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((group) => group.items);
