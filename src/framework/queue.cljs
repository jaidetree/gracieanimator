(ns framework.queue
  (:require
    [promesa.core :as p]
    ["stream" :refer [Transform Writable]]))

(defn create
  []
  (Transform.
    #js {:objectMode true
         :transform (fn [action-fn _encoding done]
                      (done nil action-fn))}))


(defn action-handler
  [promise-fn resolve]
  (fn []
    (p/let [results (promise-fn)]
      (resolve results)
      results)))

(defn enqueue
  [queue-stream promise-fn]
  (p/create
    (fn [resolve _reject]
      (.write queue-stream (action-handler promise-fn resolve)))))

(defn begin!
  [queue-stream]
  (.pipe queue-stream
         (Writable.
           #js {:objectMode true
                :write (fn [action-fn _encoding done]
                         (p/do
                           (action-fn)
                           (done)))})))

