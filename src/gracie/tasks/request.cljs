(ns gracie.tasks.request
  (:require
    [clojure.pprint :refer [pprint]]
    [promesa.core :as p]))

(defn -main
  [& args]
  (p/let [response (js/fetch "http://localhost:3000/")]
    (js/console.log response.headers)))
