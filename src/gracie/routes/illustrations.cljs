(ns gracie.routes.illustrations
  (:require [clojure.pprint :refer [pprint]]
            [gracie.projects2 :as projects]))

(defn view
  [_req {:keys [projects]}]
  (let [illustrations (->> projects
                           (filter #(projects/project-type? % :illustrations)))]
   [:div [:h1.mb-8 "Illustrations"]
    [:div.illustrations.space-y-8
     (for [illustration illustrations]
       [:img
        {:src (:image-url illustration)
         :alt (:title illustration)}])]]))
