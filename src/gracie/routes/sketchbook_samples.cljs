(ns gracie.routes.sketchbook-samples
  (:require
   [clojure.pprint :refer [pprint]]
   [gracie.projects2 :as projects]
   [clojure.string :as s]))

(defn view
  [req {:keys [projects]}]
  (let [images (->> projects
                    (filter #(projects/project-type? % :sketchbook-samples)))]
    {:status 200
     :session (:session req)
     :title "Sketchbook Samples"
     :view
     [:div
      [:h1.mb-8 "Sketchbook Samples"]
      [:div.sketchbook-samples.space-y-8
       (for [image images]
         [:img
          {:key (:slug image)
           :src (:image-url image)
           :alt (:title image)}])]]}))

