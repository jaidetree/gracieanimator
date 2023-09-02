(ns gracie.features.sketchbook-samples
 (:require
  [promesa.core :as p]
  [framework.assets :refer [fetch-image]]
  [gracie.data-pipeline :refer [defhook]]))

(defhook :sketchbook-samples :parse-project
 (fn sketchbook-samples-parse-project
  [original-project]
  {:id               (get original-project :id)
   :slug             (get original-project :slug)
   :title            (get original-project :title)
   :type             (get original-project :type)
   :featured         (= (get-in original-project [:properties :featured :checkbox]) true)
   :published        (= (get-in original-project [:properties :published :checkbox]) true)
   :image-url        (get-in original-project [:properties :image :files 0 :file :url])}))

(defhook :sketchbook-samples :queue-requests
 (fn sketchbook-samples-queue-requests
   [project]
   [{:id (:image-url project)
     :fetch #(fetch-image project "sketchbook-samples" (:image-url project))
     :reducer #(assoc %1 :image-url %2)}]))

(defhook :sketchbook-samples :format-project
 (fn sketchbook-samples-format-project
  [{:keys [project responses]}]
  (let [{:keys [image-url]} responses]
   (assoc project
          :image-url image-url
          :thumbnail image-url))))
