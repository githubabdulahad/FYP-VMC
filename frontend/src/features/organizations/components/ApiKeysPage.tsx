import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getOrganizations,
  getApiKeys,
  createApiKey,
  revokeApiKey,
} from "../api/organizationsApi";

const SCOPE_OPTIONS = ["submit", "read", "review"] as const;

function ApiKeysPage() {
  const queryClient = useQueryClient();
  const [selectedOrgId, setSelectedOrgId] = useState<number | "">("");
  const [label, setLabel] = useState("");
  const [scopes, setScopes] = useState<string[]>(["submit", "read"]);
  const [newRawKey, setNewRawKey] = useState<string | null>(null);

  const { data: organizations = [] } = useQuery({
    queryKey: ["organizations"],
    queryFn: getOrganizations,
  });

  const { data: apiKeys = [], isLoading } = useQuery({
    queryKey: ["api-keys"],
    queryFn: () => getApiKeys(),
  });

  const createMutation = useMutation({
    mutationFn: createApiKey,
    onSuccess: (created) => {
      setNewRawKey(created.raw_key);
      setLabel("");
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: revokeApiKey,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });

  const toggleScope = (scope: string) => {
    setScopes((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope]
    );
  };

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrgId || !label.trim() || scopes.length === 0) return;
    createMutation.mutate({ organization: selectedOrgId as number, label: label.trim(), scopes });
  };

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      <h1 className="text-xl font-semibold text-slate-900 mb-1">API Key Management</h1>
      <p className="text-sm text-slate-500 mb-6">
        Provision and revoke machine-client credentials for partner organizations.
      </p>

      {/* One-time raw key reveal */}
      {newRawKey && (
        <div className="mb-6 p-4 rounded-lg border border-amber-300 bg-amber-50">
          <p className="text-sm font-medium text-amber-900 mb-2">
            New key created — copy it now, it won't be shown again:
          </p>
          <code className="block text-sm bg-white border border-amber-200 rounded px-3 py-2 break-all">
            {newRawKey}
          </code>
          <button
            className="mt-2 text-xs text-amber-700 underline"
            onClick={() => setNewRawKey(null)}
          >
            I've copied it, dismiss
          </button>
        </div>
      )}

      {/* Create form */}
      <form onSubmit={handleCreate} className="mb-8 p-4 rounded-lg border border-slate-200 bg-white">
        <div className="mb-3">
          <label className="block text-sm font-medium text-slate-700 mb-1">Organization</label>
          <select
            className="w-full border border-slate-300 rounded px-3 py-2 text-sm"
            value={selectedOrgId}
            onChange={(e) => setSelectedOrgId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">Select an organization…</option>
            {organizations.map((org) => (
              <option key={org.id} value={org.id}>
                {org.name} ({org.review_mode})
              </option>
            ))}
          </select>
        </div>

        <div className="mb-3">
          <label className="block text-sm font-medium text-slate-700 mb-1">Label</label>
          <input
            type="text"
            className="w-full border border-slate-300 rounded px-3 py-2 text-sm"
            placeholder="e.g. Acme Claims System - prod"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
          />
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 mb-1">Scopes</label>
          <div className="flex gap-4">
            {SCOPE_OPTIONS.map((scope) => (
              <label key={scope} className="flex items-center gap-1.5 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={scopes.includes(scope)}
                  onChange={() => toggleScope(scope)}
                />
                {scope}
              </label>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={createMutation.isPending || !selectedOrgId || !label.trim() || scopes.length === 0}
          className="bg-slate-900 text-white text-sm font-medium px-4 py-2 rounded disabled:opacity-40"
        >
          {createMutation.isPending ? "Creating…" : "Generate API Key"}
        </button>

        {createMutation.isError && (
          <p className="mt-2 text-sm text-red-600">Failed to create key. Check the form and try again.</p>
        )}
      </form>

      {/* Existing keys */}
      <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-left">
            <tr>
              <th className="px-4 py-2 font-medium">Organization</th>
              <th className="px-4 py-2 font-medium">Label</th>
              <th className="px-4 py-2 font-medium">Key</th>
              <th className="px-4 py-2 font-medium">Scopes</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium">Last used</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={7} className="px-4 py-6 text-center text-slate-400">Loading…</td></tr>
            )}
            {!isLoading && apiKeys.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-6 text-center text-slate-400">No API keys yet.</td></tr>
            )}
            {apiKeys.map((key) => (
              <tr key={key.id} className="border-t border-slate-100">
                <td className="px-4 py-2">{key.organization_name}</td>
                <td className="px-4 py-2">{key.label}</td>
                <td className="px-4 py-2 font-mono text-xs text-slate-500">{key.key_prefix}…</td>
                <td className="px-4 py-2 text-xs text-slate-500">{key.scopes.join(", ")}</td>
                <td className="px-4 py-2">
                  {key.is_active ? (
                    <span className="text-xs text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">Active</span>
                  ) : (
                    <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded">Revoked</span>
                  )}
                </td>
                <td className="px-4 py-2 text-xs text-slate-500">
                  {key.last_used_at ? new Date(key.last_used_at).toLocaleString() : "Never"}
                </td>
                <td className="px-4 py-2 text-right">
                  {key.is_active && (
                    <button
                      className="text-xs text-red-600 hover:underline disabled:opacity-40"
                      disabled={revokeMutation.isPending}
                      onClick={() => revokeMutation.mutate(key.id)}
                    >
                      Revoke
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default ApiKeysPage;