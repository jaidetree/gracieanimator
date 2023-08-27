(ns tests.gracie.load-projects
  (:require
    [clojure.pprint :refer [pprint]]
    [promesa.core :as p]
    [gracie.data-pipeline :as dp]
    [gracie.features.storyboards]
    [gracie.features.illustrations]
    [gracie.features.sketchbook-samples]
    [gracie.features.comics]))

(defn -main
  [& args]
  (p/-> (dp/fetch!)
        (pprint)))
