(ns framework.env
  (:require
   [clojure.string :as s]
   [clojure.edn :as edn]
   [framework.utils :refer [read-file]]))

(defn parse-ini-line
  [ini-line]
  (loop [remaining ini-line
         name ""]
    (let [[c & remaining] remaining]
      (case c
        "=" (str "[:" name " " (s/join "" remaining) "]")
        (recur remaining (str name c))))))

(defn wrap-pairs
  [pairs-str]
  (str "[" pairs-str "]"))

(defn read-ini-file
  [filename]
  (try
    (read-file filename)
    (catch js/Error error
      (js/console.error error)
      "")))

(def env
  (->> (s/split (read-ini-file ".env") #"\n")
       (map parse-ini-line)
       (s/join "\n")
       (wrap-pairs)
       (edn/read-string)
       (into {})))

(defn optional
  [key default]
  (let [value (get env (keyword key) ::not-found)]
    (if (= value ::not-found)
      (do
        (js/console.warn (str "Optional: Could not find ENV var " key))
        default)
      value)))

(defn required
  [key]
  (let [value (get env (keyword key) ::not-found)]
    (if (= value ::not-found)
      (throw (js/Error. (str "Required: Could not find ENV var " key))))
      value))
