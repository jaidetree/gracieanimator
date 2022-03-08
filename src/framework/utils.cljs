(ns framework.utils
  (:require
   [clojure.edn :as edn]
   [clojure.pprint :refer [pprint]]
   ["fs" :as fs]))

(defn pprint-str
  [data]
  (with-out-str
    (pprint data)))

(defn read-file
  [filename]
  (.readFileSync fs filename #js {:encoding "utf-8"}))

(defn read-edn-file
  [filename]
  (-> filename
      (read-file)
      (edn/read-string)))

(defn write-edn-file
  [filename contents]
  (.writeFileSync fs filename (pprint-str contents) #js {:encoding "utf-8"}))
