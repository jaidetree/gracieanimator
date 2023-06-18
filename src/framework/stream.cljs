(ns framework.stream
  (:require
    ["baconjs" :as bacon]))

(def Bus (.-Bus bacon))

(defn bus
  []
  (Bus.))

(def of (.-once bacon))

(defn next
  [x]
  (new (.-Next bacon) x))

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

