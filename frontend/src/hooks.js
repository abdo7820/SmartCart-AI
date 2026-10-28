import { useEffect, useState } from "react";
import { get } from "./api";

export function useGet(path, params) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const key = path + JSON.stringify(params || {});
  const load = (live = true) => {
    setState((s) => ({ ...s, loading: true, error: null }));
    return get(path, params)
      .then((data) => { if (live) setState({ data, error: null, loading: false }); return data; })
      .catch((error) => { if (live) setState({ data: null, error, loading: false }); throw error; });
  };
  useEffect(() => {
    let live = true;
    load(live).catch(() => {});
    return () => {
      live = false;
    };
  }, [key]);
  return { ...state, refresh: () => load(true) };
}
