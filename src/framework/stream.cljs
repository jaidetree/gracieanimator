(ns framework.stream
  (:require
    ["baconjs" :as bacon]
    ["stream" :refer [PassThrough]]))

(def Bus (.-Bus bacon))

(defn bus
  []
  (Bus.))

(def of (.-once bacon))

(defn next
  [x]
  (new (.-Next bacon) x))

(def never (.-never bacon))

(defn error
  [x]
  (new (.-Error bacon) x))

(defn end
  []
  (new (.-End bacon)))

(defn create
  [f]
  (.fromBinder bacon f))

(defn from-seq
  [coll]
  (create
    (fn [push]
      (doseq [x coll]
        (push (next x)))
      (push (end)))))

(defn from-promise
  [promise]
  (.fromPromise bacon promise true))

(defn to-readable
  [source]
  (let [dest (PassThrough. #js {:objectMode true})
        unsub (.subscribe source
                          (fn [event]
                            (cond
                              (.-isError event) (.push dest (.-value event))
                              (.-isEnd event) (.end dest)
                              (.-hasValue event) (.write dest (.-value event)))))]
    (.once dest "finish" unsub)
    (.once dest "error" unsub)
    dest))

(defn pipe
  [source dest]
  (let [unsub (.subscribe source
                          (fn [event]
                            (cond
                              (.-isError event) (.push dest (.-value event))
                              (.-isEnd event) (.end dest)
                              (.-hasValue event) (.write dest (.-value event)))))]
    (.once dest "finish" unsub)
    (.once dest "error" unsub)
    dest))

(defn merge-all
  [streams]
  (.mergeAll bacon (clj->js streams)))
