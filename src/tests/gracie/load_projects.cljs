(ns tests.gracie.load-projects
  (:require
    [gracie.features.storyboards]
    [gracie.data-pipeline :as dp]))

(defn -main
  [& args]
  (dp/fetch!))

