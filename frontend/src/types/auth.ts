export interface Organization {
  id: number;
  name: string;
  slug: string;
  review_mode: "assisted" | "direct";
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  organization: Organization | null;
  can_review_partner_submissions?: boolean;
  is_staff?: boolean;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  setUser: (user: User) => void;
  clearUser: () => void;
}