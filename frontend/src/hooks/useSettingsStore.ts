import { useCallback, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getSettings, updateSettings } from "@/api/client";

export function useSettingsStore() {
  const queryClient = useQueryClient();
  const { data: categories, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: getSettings,
  });

  const flat = useMemo(() => {
    const map: Record<string, string> = {};
    if (categories) {
      for (const cat of categories) {
        for (const s of cat.settings) {
          map[s.key] = s.value ?? "";
        }
      }
    }
    return map;
  }, [categories]);

  const get = useCallback((key: string, fallback = "") => flat[key] ?? fallback, [flat]);
  const getBool = useCallback((key: string) => flat[key] === "true", [flat]);

  const save = useCallback(
    async (values: Record<string, string>) => {
      await updateSettings(values);
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
    [queryClient]
  );

  return { get, getBool, save, loaded: !isLoading && !!categories };
}
