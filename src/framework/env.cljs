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
      (println "Could not read .env file" filename)
      #_(js/console.error error)
      nil)))

(defn pe
  [env]
  (println env)
  env)

(def env
  (when-let [contents (or (read-ini-file ".env")
                          (read-ini-file "/etc/secrets/.env"))]
    (some->> (s/split contents #"\n")
             (map parse-ini-line)
             (println (s/join "\n"))
             (s/join "\n")
             (wrap-pairs)
             (edn/read-string)
             (into {})
             #_(pe))))

(defn optional
  [key default]
  (let [kw (keyword key)
        value (or (aget js/process.env (name kw))
                  (get env kw)
                  ::not-found)]
    (if (= value ::not-found)
      (do
        (js/console.warn (str "Optional: Could not find ENV var " key))
        default)
      value)))

(defn required
  [key]
  (let [kw (keyword key)
        value (or (aget js/process.env (name kw))
                  (get env kw)
                  ::not-found)]
    (when (= value ::not-found)
      (throw (js/Error. (str "Required: Could not find ENV var " key))))
    value))
