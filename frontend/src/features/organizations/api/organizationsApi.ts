import api from "../../../lib/axios";

export interface Organization {
  id: number;
  name: string;
  slug: string;
  review_mode: "assisted" | "direct";
  is_active: boolean;
  created_at: string;
}

export interface OrganizationAPIKey {
  id: number;
  organization: number;
  organization_name: string;
  label: string;
  key_prefix: string;
  scopes: ("submit" | "read" | "review")[];
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
}

export interface CreatedAPIKey extends OrganizationAPIKey {
  raw_key: string; // only present on the create response, never again
}

export const getOrganizations = async (includeInactive = false): Promise<Organization[]> => {
  const response = await api.get("/organizations/", {
    params: includeInactive ? { include_inactive: "true" } : undefined,
  });
  return response.data;
};

export const createOrganization = async (payload: {
  name: string;
  review_mode?: "assisted" | "direct";
}): Promise<Organization> => {
  const response = await api.post("/organizations/", payload);
  return response.data;
};

export const updateOrganization = async (
  orgId: number,
  payload: { name?: string; review_mode?: "assisted" | "direct" }
): Promise<Organization> => {
  const response = await api.patch(`/organizations/${orgId}/`, payload);
  return response.data;
};

export const deactivateOrganization = async (orgId: number): Promise<Organization> => {
  const response = await api.delete(`/organizations/${orgId}/`);
  return response.data;
};

export const deleteOrganization = async (orgId: number): Promise<void> => {
  await api.delete(`/organizations/${orgId}/`, { params: { hard: "true" } });
};

export const reactivateOrganization = async (orgId: number): Promise<Organization> => {
  const response = await api.post(`/organizations/${orgId}/reactivate/`);
  return response.data;
};

export const getApiKeys = async (organizationId?: number): Promise<OrganizationAPIKey[]> => {
  const response = await api.get("/organizations/api-keys/", {
    params: organizationId ? { organization: organizationId } : undefined,
  });
  return response.data;
};

export const createApiKey = async (payload: {
  organization: number;
  label: string;
  scopes: string[];
}): Promise<CreatedAPIKey> => {
  const response = await api.post("/organizations/api-keys/", payload);
  return response.data;
};

export const revokeApiKey = async (keyId: number): Promise<OrganizationAPIKey> => {
  const response = await api.post(`/organizations/api-keys/${keyId}/revoke/`);
  return response.data;
};