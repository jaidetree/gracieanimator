(ns gracie.tasks.build-cache
  (:require
    #_[clojure.pprint :refer [pprint]]
    [promesa.core :as p]
    [gracie.data-pipeline :as dp]
    [gracie.features.storyboards]
    [gracie.features.illustrations]
    [gracie.features.sketchbook-samples]
    [gracie.features.comics]))

(defn log
  [action]
  (prn action))

(defn -main
  [& _args]
  (p/do
    (dp/fetch! log)
    (println "Cache built in .cache")))
