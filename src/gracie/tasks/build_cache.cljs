(ns gracie.tasks.build-cache
  (:require
    #_[clojure.pprint :refer [pprint]]
    [promesa.core :as p]
    [gracie.data-pipeline :as dp]
    [gracie.features.storyboards]
    [gracie.features.illustrations]
    [gracie.features.sketchbook-samples]
    [gracie.features.comics]))

(defn -main
  [& _args]
  (p/do
    (dp/fetch!)
    (println "Cache built in .cache")))
