(ns gracie.tasks.deploy
  (:require
    [clojure.string :as s]
    [framework.env :as env]))

(defn generate-dockerfile-config
  []
  (->> (for [[key value] env/env]
         (when (not= key :PORT)
           (str "  --mount-type=secret,id=" (name key))))
       (filter identity)
       (s/join " \\\n")
       (println)))

(defn deploy
  [])

(defn help
  []
  (println "yarn deploy (now | dockerfile)"))

(defn -main
  [target & args]
  (case target
    "dockerfile" (generate-dockerfile-config)
    "now"        (deploy)
    "help"       (help)
    (help)))


