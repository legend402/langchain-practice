import { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import { knowledgeApi } from "../api/knowledgeApi";
import type { ParseTask, ParseTaskStatus } from "../types/knowledge";

interface ParseTaskContextValue {
  tasks: ParseTask[];
  startTask: (taskId: string) => void;
  isTaskActive: (taskId: string) => boolean;
  getTaskStatus: (taskId: string) => ParseTask | undefined;
}

const ParseTaskContext = createContext<ParseTaskContextValue>({
  tasks: [],
  startTask: () => {},
  isTaskActive: () => false,
  getTaskStatus: () => undefined,
});

const STATUS_ORDER: Record<ParseTaskStatus, number> = {
  pending: 0,
  parsing: 1,
  enriching_images: 2,
  walking_cache: 3,
  chunking: 4,
  embedding: 5,
  storing: 6,
  completed: 7,
  failed: 8,
};

function parseSseData(raw: string): ParseTask | null {
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function ParseTaskProvider({ children }: { children: React.ReactNode }) {
  const [tasks, setTasks] = useState<ParseTask[]>([]);
  const watchersRef = useRef<Map<string, EventSource>>(new Map());

  const updateTask = useCallback((task: ParseTask) => {
    setTasks((prev) => {
      const idx = prev.findIndex((t) => t.task_id === task.task_id);
      if (idx >= 0) {
        const existing = prev[idx];
        if (STATUS_ORDER[task.status] <= STATUS_ORDER[existing.status]) return prev;
        const next = [...prev];
        next[idx] = task;
        return next;
      }
      return [...prev, task];
    });
  }, []);

  const removeTask = useCallback((taskId: string) => {
    setTasks((prev) => prev.filter((t) => t.task_id !== taskId));
  }, []);

  const stopWatcher = useCallback((taskId: string) => {
    const es = watchersRef.current.get(taskId);
    if (es) {
      es.close();
      watchersRef.current.delete(taskId);
    }
  }, []);

  const startWatcher = useCallback(
    (taskId: string) => {
      if (watchersRef.current.has(taskId)) return;

      const es = knowledgeApi.watchTaskProgress(taskId);

      es.onmessage = (event) => {
        const task = parseSseData(event.data);
        if (!task) return;

        updateTask({ ...task, task_id: taskId });

        if (task.status === "completed" || task.status === "failed") {
          setTimeout(() => {
            stopWatcher(taskId);
            removeTask(taskId);
          }, 3000);
        }
      };

      es.onerror = () => {
        stopWatcher(taskId);
      };

      watchersRef.current.set(taskId, es);
    },
    [updateTask, stopWatcher, removeTask],
  );

  const startTask = useCallback(
    (taskId: string) => {
      updateTask({ task_id: taskId, status: "pending", detail: "等待解析...", entry_id: "" });
      startWatcher(taskId);
    },
    [updateTask, startWatcher],
  );

  useEffect(() => {
    let cancelled = false;

    async function recover() {
      try {
        const activeTasks = await knowledgeApi.listActiveTasks();
        if (cancelled) return;
        for (const task of activeTasks) {
          if (task.status !== "completed" && task.status !== "failed") {
            updateTask(task);
            startWatcher(task.task_id);
          }
        }
      } catch {
        // ignore recovery errors
      }
    }

    recover();
    return () => {
      cancelled = true;
      watchersRef.current.forEach((es) => es.close());
      watchersRef.current.clear();
    };
  }, [updateTask, startWatcher]);

  const isTaskActive = useCallback(
    (taskId: string) => tasks.some((t) => t.task_id === taskId),
    [tasks],
  );

  const getTaskStatus = useCallback(
    (taskId: string) => tasks.find((t) => t.task_id === taskId),
    [tasks],
  );

  return (
    <ParseTaskContext.Provider value={{ tasks, startTask, isTaskActive, getTaskStatus }}>
      {children}
    </ParseTaskContext.Provider>
  );
}

export function useParseTask() {
  return useContext(ParseTaskContext);
}
